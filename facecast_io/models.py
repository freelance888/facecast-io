from __future__ import annotations

from typing import List, Optional, Union, Any

import attr
from attr import dataclass

from .entities import (
    AvailableServers,
    DeviceStatusFull,
    DeviceOutput as BaseDeviceOutput,
)
from .logger_setup import logger
from .server_connector import ServerConnector


@dataclass
class DeviceOutput:
    device: Device
    output: BaseDeviceOutput

    def start(self):
        return self.device.server_connector.start_output(
            self.device.rtmp_id, self.output.id
        )

    def stop(self):
        return self.device.server_connector.stop_output(
            self.device.rtmp_id, self.output.id
        )

    def delete(self):
        return self.device.server_connector.delete_output(
            self.device.rtmp_id, self.output.id
        )


@dataclass
class Device:
    server_connector: ServerConnector
    name: str
    rtmp_id: str
    online: Optional[bool] = None
    type: Optional[str] = None
    lang: Optional[str] = None
    updates: Optional[bool] = None
    outputs: List[DeviceOutput] = attr.attrib(factory=list)
    status: Optional[DeviceStatusFull] = None
    available_servers: Optional[AvailableServers] = None

    def _update_device_info(self):
        device_data = self.server_connector.get_device(self.rtmp_id)
        self.online = device_data.online
        self.type = device_data.type
        self.lang = device_data.lang
        self.updates = device_data.updates

    @property
    def main_server_url(self) -> str:
        return self.status.main_server_url

    @property
    def backup_server_url(self) -> str:
        if self.status.backup_server_id == 0:
            return ""
        return self.available_servers[self.status.backup_server_id].url

    @property
    def shared_key(self):
        return self.status.shared_key

    def _update_device_status(self):
        self.status = self.server_connector.get_status(self.rtmp_id)

    def _update_outputs(self):
        device_outputs = self.server_connector.get_outputs(self.rtmp_id)
        self.outputs.clear()
        for o in device_outputs:
            do = DeviceOutput(device=self, output=o)
            self.outputs.append(do)

    def _update_available_servers(self):
        self.available_servers = self.server_connector.get_available_servers(
            self.rtmp_id
        )

    def update(self):
        self._update_device_info()
        self._update_device_status()
        self._update_outputs()
        self._update_available_servers()

    def create_output(self, name, server_url, shared_key, audio=0) -> bool:
        device_output = self.server_connector.create_output(
            self.rtmp_id,
            server_url=server_url,
            shared_key=shared_key,
            title=name,
            audio=audio,
        )
        if not device_output.ok:
            logger.error(device_output.msg)
            return False
        self._update_outputs()
        return True

    def start_outputs(self):
        logger.info(f"start_outputs: {self.name}")
        for o in self.outputs:
            logger.debug(o.start())
        self._update_outputs()
        return True

    def stop_outputs(self):
        logger.info(f"stop_outputs: {self.name}")
        for o in self.outputs:
            logger.debug(o.stop())
        self._update_outputs()
        return True

    def delete_outputs(self):
        logger.info(f"delete_outputs: {self.name}")
        for o in self.outputs:
            logger.debug(o.delete())
        self._update_outputs()
        return True

    def delete(self):
        logger.info(f"delete_device: {self.name}")
        self.delete_outputs()
        self.server_connector.delete_device(self.rtmp_id)
        return True

    def select_server(self, server_id: Union[int, str]) -> bool:
        self._update_available_servers()
        if self.available_servers and str(server_id) not in self.available_servers:
            raise Exception("Not allowed server_id")
        if self.server_connector.select_server(self.rtmp_id, server_id):
            self._update_device_status()
        return True

    def select_fastest_server(self) -> bool:
        self._update_available_servers()
        if self.server_connector.select_server(
            self.rtmp_id, self.available_servers[0].id
        ):
            self._update_device_status()
        return True
