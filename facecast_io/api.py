from __future__ import absolute_import

import os
from typing import List, Optional, cast

import httpx

from .entities import Stream
from .logger_setup import logger
from .models import Device, Devices
from .server_connector import (
    ServerConnector,
    BASE_HEADERS,
    POSSIBLE_BASE_URLS,
)
from .errors import DeviceNotFound


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
        self.devices: Devices = Devices(self.server_connector)
        self.devices.update()

    @property
    def is_authorized(self):
        return self.server_connector.is_authorized

    def do_auth(self, username, password):
        return self.server_connector.do_auth(username, password)

    def get_devices(self, *, update=False) -> Devices:
        if update:
            self.devices.update()
        return self.devices

    def delete_device(self, name):
        self.devices.delete_device(name)

    def create_new_device(self, name: str) -> Device:
        return self.devices.create_device(name)

    def get_or_create_device(self, name: str) -> Device:
        try:
            return self.devices[name]
        except DeviceNotFound:
            return self.devices.create_device(name)

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
        self.devices.update()
        return device

    def get_device(self, name, update=False) -> Optional[Device]:
        return self.devices.get_device(name)
