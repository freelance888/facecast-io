from __future__ import absolute_import

import os
from typing import List, Optional, cast

import httpx
from retry.api import retry_call  # type: ignore

from .entities import Stream
from .logger_setup import logger
from .models import Device
from .server_connector import (
    ServerConnector,
    BASE_HEADERS,
    POSSIBLE_BASE_URLS,
)
from .errors import DeviceNotFound, FacecastAPIError


def find_available_server():
    with httpx.Client(proxies=os.getenv("HTTP_PROXY"), verify=False) as client:
        for url in POSSIBLE_BASE_URLS:
            r = client.get(url)
            if r.status_code in [200, 201]:
                return url


class FacecastAPI:
    def __init__(self, username: str = None, password: str = None):
        self.client = httpx.Client(
            proxies=os.getenv("HTTP_PROXY"),
            base_url=find_available_server(),
            verify=False,
            headers=BASE_HEADERS,
        )
        self.server_connector = ServerConnector(self.client)
        if username and password:
            self.do_auth(username, password)
        self._devices = []

    @property
    def is_authorized(self):
        return self.server_connector.is_authorized

    def do_auth(self, username, password):
        return self.server_connector.do_auth(username, password)

    def get_devices(self, *, update=False) -> List[Device]:
        if self._devices and not update:
            return self._devices
        for d in self.server_connector.get_devices():
            device = Device(
                server_connector=self.server_connector, name=d.name, rtmp_id=d.rtmp_id,
            )
            if update:
                device.update()
            self._devices.append(device)
        return self._devices

    def delete_device(self, name):
        dev = self.get_device(name)
        outputs = self.server_connector.get_outputs(dev.rtmp_id)
        for o in outputs:
            self.server_connector.delete_output(dev.rtmp_id, o.id)
        self.server_connector.delete_device(dev.rtmp_id)

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
            device.update()
            device.select_fastest_server()
            return device
        raise FacecastAPIError("Some error happened during creation")

    def get_or_create_device(self, name: str) -> Device:
        try:
            return cast(Device, self.get_device(name, update=True))
        except DeviceNotFound:
            return cast(Device, self.create_new_device(name))

    def create_device_and_outputs(self, name, streams_data: List[Stream]) -> Device:
        device = self.get_or_create_device(name)
        device.delete_outputs()
        for stream in streams_data:
            output = device.create_output(
                name=stream.name,
                server_url=stream.server_url,
                shared_key=stream.shared_key,
            )
            logger.info(f"{device.name} {output}")
        return cast(Device, device)

    def get_device(self, name, update=False) -> Optional[Device]:
        devices = [d for d in self.get_devices(update=True) if d.name == name]
        if devices:
            device = devices[-1]
            if update:
                device.update()
            return cast(Device, device)
        raise DeviceNotFound(f"{name}")

    def start_outputs(self):
        for d in self.get_devices():
            d.start_outputs()
            logger.info(f"Started for device {d.name}")

    def stop_outputs(self):
        for d in self.get_devices():
            d.stop_outputs()
            logger.info(f"Stopped for device {d.name}")
