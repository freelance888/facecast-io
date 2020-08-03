from __future__ import annotations

from typing import Optional, Sequence, List, Dict

from attr import dataclass
from retry.api import retry_call

from .errors import FacecastAPIError, DeviceNotFound
from .entities import (
    AvailableServers,
    DeviceStatusFull,
    DeviceOutput as BaseDeviceOutput,
    DeviceInfo,
)
from .logger_setup import logger
from .server_connector import ServerConnector


@dataclass
class DeviceOutput:
    device: Device
    output: BaseDeviceOutput

    def __str__(self):
        return f"Output <{self.output.title}>"

    def start(self):
        return self.device._server_connector.start_output(
            self.device.rtmp_id, self.output.id
        )

    def stop(self):
        return self.device._server_connector.stop_output(
            self.device.rtmp_id, self.output.id
        )

    def delete(self):
        return self.device._server_connector.delete_output(
            self.device.rtmp_id, self.output.id
        )


class DeviceOutputs(Sequence[DeviceOutput]):
    def __init__(self, device: Device):
        self._device = device
        self._server_connector = device._server_connector
        self.rtmp_id = device.rtmp_id
        self._outputs = []

    def __str__(self):
        return "Outputs <{}>".format("\n".join(str(o) for o in self._outputs))

    def __getitem__(self, item) -> Device:
        if isinstance(item, int):
            compare_by = lambda d: d.id
        elif isinstance(item, str):
            compare_by = lambda d: d.name
        else:
            raise DeviceNotFound(f"{item}")
        for device in self._outputs:
            if compare_by(device):
                return device
            raise DeviceNotFound(f"{item}")

    def __len__(self):
        return len(self._outputs)

    def __iter__(self):
        yield from self._outputs

    def clear(self):
        self._outputs.clear()

    def update_outputs(self):
        device_outputs = self._server_connector.get_outputs(self.rtmp_id)
        self._outputs.clear()
        for o in device_outputs:
            do = DeviceOutput(device=self._device, output=o)
            self._outputs.append(do)

    def start_outputs(self):
        for o in self:
            logger.debug(o.start())
        return True

    def stop_outputs(self):
        for o in self:
            logger.debug(o.stop())
        return True


class Device:
    def __init__(self, server_connector: ServerConnector, name: str, rtmp_id: int):
        self._server_connector = server_connector
        self.name = name
        self.rtmp_id = rtmp_id

        self.outputs: DeviceOutputs = DeviceOutputs(self)
        self._info: Optional[DeviceInfo] = None
        self._status: Optional[DeviceStatusFull] = None
        self._available_servers: Optional[AvailableServers] = None
        self._stream_server_selected = False

    def __repr__(self):
        return f"Device <{self.name} - {self.rtmp_id}>"

    def __str__(self):
        return f"Device <{self.name}: {self.outputs}>"

    @property
    def main_server_url(self) -> str:
        return self._status.main_server_url

    @property
    def backup_server_url(self) -> str:
        if self._status.backup_server_id == 0:
            return ""
        return self._available_servers[self._status.backup_server_id].url

    @property
    def shared_key(self):
        return self._status.shared_key

    @property
    def input_params(self) -> Dict[str, str]:
        return {
            "lang_code": self.name,
            "main_server_url": self.main_server_url,
            "backup_server_url": self.backup_server_url,
            "shared_key": self.shared_key,
        }

    def _update_device_status(self):
        self._status = self._server_connector.get_status(self.rtmp_id)

    def _update_outputs(self):
        self.outputs.update_outputs()

    def _update_available_servers(self):
        self._available_servers = self._server_connector.get_available_servers(
            self.rtmp_id
        )

    def update(self):
        self._info = self._server_connector.get_device(self.rtmp_id)
        self._update_device_status()
        self._update_outputs()
        self._update_available_servers()
        if not self._stream_server_selected:
            self.select_fastest_server()

    def create_output(self, name, server_url, shared_key, audio=0) -> bool:
        device_output = self._server_connector.create_output(
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
        self.outputs.start_outputs()
        self._update_outputs()
        return True

    def stop_outputs(self):
        logger.info(f"stop_outputs: {self.name}")
        self.outputs.stop_outputs()
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
        self._server_connector.delete_device(self.rtmp_id)
        return True

    def select_server(self, server_id: int):
        self._update_available_servers()
        if self._available_servers and server_id not in self._available_servers:
            raise FacecastAPIError("Not allowed server_id")
        if self._server_connector.select_server(self.rtmp_id, server_id):
            self._update_device_status()
            self._stream_server_selected = True

    def select_fastest_server(self):
        self._update_available_servers()
        if self._server_connector.select_server(
            self.rtmp_id, self._available_servers.fastest.id
        ):
            self._update_device_status()
            self._stream_server_selected = True


class Devices(Sequence[Device]):
    def __init__(self, server_connector):
        self._server_connector = server_connector
        self._devices: List[Device] = []

    def __repr__(self):
        return f"Devices <{self._devices}>"

    def __str__(self):
        return "Devices <{}>".format("\n".join(str(d) for d in self._devices))

    def __getitem__(self, item) -> Device:
        if isinstance(item, int):
            compare_by = lambda d, item: d.rtmp_id == item
        elif isinstance(item, str):
            compare_by = lambda d, item: d.name == item
        else:
            raise DeviceNotFound(f"{item}")
        for device in self._devices:
            if compare_by(device, item):
                return device
        raise DeviceNotFound(f"{item}")

    def __len__(self):
        return len(self._devices)

    def __iter__(self):
        yield from self._devices

    def __contains__(self, item):
        try:
            self[item]
            return True
        except DeviceNotFound:
            return False

    def get_device(self, name: str):
        self.update()
        device = self[name]
        return device

    def delete_device(self, name: str):
        dev = self.get_device(name)
        outputs = self._server_connector.get_outputs(dev.rtmp_id)
        for o in outputs:
            self._server_connector.delete_output(dev.rtmp_id, o.id)
        if self._server_connector.delete_device(dev.rtmp_id):
            self._devices.remove(dev)
            return
        raise FacecastAPIError(f"Failed to delete `{name}`")

    def delete_all(self):
        for d in self._devices:
            d.delete()
        self._devices.clear()

    def create_device(self, name: str) -> Device:
        if self._server_connector.create_device(name):
            device = retry_call(
                self.get_device,
                fargs=[name],
                exceptions=DeviceNotFound,
                tries=3,
                delay=4,
            )
            return device
        raise FacecastAPIError("Some error happened during creation")

    def start_outputs(self):
        for d in self._devices:
            d.start_outputs()
            logger.info(f"Started for device {d.name}")

    def stop_outputs(self):
        for d in self._devices:
            d.stop_outputs()
            logger.info(f"Stopped for device {d.name}")

    def _add_new_devices(self):
        new_devices = self._server_connector.get_devices()
        for d in new_devices:
            if d.rtmp_id not in self:
                device = Device(
                    server_connector=self._server_connector,
                    name=d.name,
                    rtmp_id=d.rtmp_id,
                )
                self._devices.append(device)

    def update(self):
        self._add_new_devices()
        for d in self:
            d.update()

    @property
    def input_params(self):
        return [d.input_params for d in self._devices]
