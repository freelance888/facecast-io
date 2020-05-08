from __future__ import absolute_import

import functools
from typing import List, Optional, Literal, TypedDict, cast

import httpx

from .logger_setup import logger
from .models import Device
from .core.server_connector import (
    ServerConnector,
    BASE_URL,
    BASE_HEADERS,
)


class APIError(Exception):
    ...


def auth_required(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.is_authorized:
            raise APIError("Need to authorize first")
        return func(self, *args, **kwargs)

    return wrapper


class Stream(TypedDict):
    name: str
    server_url: str
    shared_key: str


class FacecastAPI:
    def __init__(self, auth: Optional[tuple] = None):
        self.client = httpx.Client(
            base_url=BASE_URL, verify=False, headers=BASE_HEADERS,
        )
        self.server_connector = ServerConnector(self.client)
        if auth:
            self.do_auth(auth[0], auth[1])

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
            device = self.get_device(name, update=True)
            if device is None:
                raise APIError("Device didn't created")
            result = device.select_fastest_server()
            device.input.shared_key = result["sharedkey"]
            return cast(Device, device)
        raise APIError("Some error happened during creation")

    @auth_required
    def get_or_create_device(self, name: str) -> Device:
        device = self.get_device(name, update=True)
        if device:
            return cast(Device, device)
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
        return None

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
