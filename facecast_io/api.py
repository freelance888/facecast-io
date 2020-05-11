from __future__ import absolute_import

from typing import List, Optional, cast

import httpx
from retry.api import retry_call  # type: ignore

from .core.entities import Stream
from .utils import auth_required
from .logger_setup import logger
from .models import Device
from .core.server_connector import (
    ServerConnector,
    BASE_URL,
    BASE_HEADERS,
)
from .core.errors import DeviceNotFound, FacecastAPIError


class FacecastAPI:
    def __init__(self, username: str = None, password: str = None):
        self.client = httpx.Client(
            base_url=BASE_URL, verify=False, headers=BASE_HEADERS,
        )
        self.server_connector = ServerConnector(self.client)
        if username and password:
            self.do_auth(username, password)

    @property
    def is_authorized(self):
        return self.server_connector.is_authorized

    def do_auth(self, username, password):
        return self.server_connector.do_auth(username, password)

    @auth_required
    def get_devices(self, *, update=False) -> List[Device]:
        devices = []
        for d in self.server_connector.get_devices():
            device = Device(
                server_connector=self.server_connector,
                name=d["name"],
                rtmp_id=d["rtmp_id"],
            )
            if update:
                device.update()
            devices.append(device)
        return devices

    @auth_required
    def delete_device(self, name):
        dev = self.get_device(name)
        outputs = self.server_connector.get_outputs(dev.rtmp_id)
        for o in outputs:
            self.server_connector.delete_output(dev.rtmp_id, o["id"])
        self.server_connector.delete_device(dev.rtmp_id)

    @auth_required
    def create_new_device(self, name: str) -> Device:
        if self.server_connector.create_device(name):
            device = retry_call(
                self.get_device,
                fargs=[name],
                fkwargs=dict(update=True),
                exceptions=DeviceNotFound,
                tries=3,
                delay=4,
            )
            result = device.select_fastest_server()
            device.input.shared_key = result["sharedkey"]
            return cast(Device, device)
        raise FacecastAPIError("Some error happened during creation")

    @auth_required
    def get_or_create_device(self, name: str) -> Device:
        try:
            return cast(Device, self.get_device(name, update=True))
        except DeviceNotFound:
            return cast(Device, self.create_new_device(name))

    @auth_required
    def create_device_and_outputs(self, name, streams_data: List[Stream]) -> Device:
        device = self.get_or_create_device(name)
        device.delete_outputs()
        for stream in streams_data:
            output = device.create_output(
                name=stream["name"],
                server_url=stream["server_url"],
                shared_key=stream["shared_key"],
            )
            logger.info(f"{device.name} {output}")
        return cast(Device, device)

    @auth_required
    def get_device(self, name, update=False) -> Optional[Device]:
        devices = [d for d in self.get_devices() if d.name == name]
        if devices:
            device = devices[-1]
            if update:
                device.update()
            return cast(Device, device)
        raise DeviceNotFound(f"{name}")

    @auth_required
    def start_outputs(self):
        for d in self.get_devices():
            d.start_outputs()
            logger.info(f"Started for device {d.name}")

    @auth_required
    def stop_outputs(self):
        for d in self.get_devices():
            d.stop_outputs()
            logger.info(f"Stopped for device {d.name}")

    def get_devices_input(self):
        return [
            Stream(
                name=d.name,
                server_url=d.input.server_url,
                shared_key=d.input.shared_key,
            )
            for d in self.get_devices(update=True)
        ]
