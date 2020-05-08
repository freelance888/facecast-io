from __future__ import annotations

from typing import List, Optional, Union

import attr
from attr import dataclass

from .core.entities import SelectServerStatus
from .logger_setup import logger
from .core.server_connector import ServerConnector
from .utils import to_bool


@dataclass
class DeviceInputStatus:
    input: DeviceInput
    ok: bool
    msg: str
    response: bool
    status: str
    resolution: str
    fps: str
    time: float


@dataclass
class DeviceStatus:
    device: Device
    ok: bool
    ping: int
    server: str
    server_id: str
    connected: str
    input_url: str
    sharedkey: str
    time: float
    is_online: int


@dataclass
class DeviceInput:
    device: Device

    server_url: str
    shared_key: str
    status: Optional[DeviceInputStatus] = None

    def update(self):
        input_status = self.device.server_connector.get_status(self.device.rtmp_id).get(
            "input_status"
        )
        if input_status:
            self.status = DeviceInputStatus(
                input=self,
                ok=to_bool(input_status.get("ok")),
                msg=input_status.get("msg"),
                response=input_status.get("response"),
                resolution=input_status.get("resolution"),
                status=input_status.get("status"),
                fps=input_status.get("fps"),
                time=input_status.get("time"),
            )


@dataclass
class DeviceOutputStatus:
    output: DeviceOutput


@dataclass
class DeviceOutput:
    device: Device
    title: str
    enabled: bool
    type: str
    id: str
    cloud: int
    status: Optional[DeviceOutputStatus] = None

    def update(self):
        ...
        # output_status = self.device.server_connector.get_status(
        #     self.device.rtmp_id
        # ).get("get_status")
        # if output_status:
        #     self.status = DeviceOutputStatus(output=self,)

    def start(self):
        return self.device.server_connector.start_output(self.device.rtmp_id, self.id)

    def stop(self):
        return self.device.server_connector.stop_output(self.device.rtmp_id, self.id)

    def delete(self):
        return self.device.server_connector.delete_output(self.device.rtmp_id, self.id)


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
    input: Optional[DeviceInput] = None
    status: Optional[DeviceStatus] = None
    available_servers: Optional = None

    def _update_device_info(self):
        device_data = self.server_connector.get_device(self.rtmp_id)
        self.online = device_data["online"]
        self.type = device_data["type"]
        self.lang = device_data["lang"]
        self.updates = device_data["updates"]

    def _update_device_status(self):
        status = self.server_connector.get_status(self.rtmp_id).get("get_status")
        if status:
            self.status = DeviceStatus(
                device=self,
                ok=to_bool(status.get("ok")),
                ping=status.get("ping"),
                server=status.get("server"),
                server_id=status.get("server_id"),
                connected=status.get("connected"),
                input_url=status.get("input_url"),
                sharedkey=status.get("sharedkey"),
                time=status.get("time"),
                is_online=status.get("is_online"),
            )

    def _update_outputs(self):
        device_outputs = self.server_connector.get_outputs(self.rtmp_id)
        self.outputs.clear()
        for o in device_outputs:
            do = DeviceOutput(
                device=self,
                title=o["descr"],
                enabled=bool(o["enabled"]),
                type=o["type"],
                id=o["id"],
                cloud=o["cloud"],
            )
            do.update()
            self.outputs.append(do)

    def _update_available_servers(self):
        self.available_servers = self.server_connector.get_available_servers(
            self.rtmp_id
        )

    def _update_input(self):
        device_input = self.server_connector.get_input_params(self.rtmp_id)
        di = DeviceInput(
            device=self,
            server_url=device_input["server_url"],
            shared_key=device_input["shared_key"],
        )
        di.update()
        self.input = di

    def update(self):
        self._update_device_info()
        self._update_device_status()
        self._update_input()
        self._update_outputs()
        self._update_available_servers()

    def create_output(
        self, name, server_url, shared_key, audio=0
    ) -> Optional[DeviceOutput]:
        r = self.server_connector.create_output(
            self.rtmp_id,
            server_url=server_url,
            shared_key=shared_key,
            title=name,
            audio=audio,
        )
        if not to_bool(r["ok"]):
            logger.error(r["msg"])
            return None
        o = r["outputs"][0]

        do = DeviceOutput(
            device=self,
            title=o["descr"],
            enabled=bool(o["enabled"]),
            type=o["type"],
            id=o["id"],
            cloud=o["cloud"],
        )
        do.update()
        self.outputs.append(do)
        return do

    def start_outputs(self):
        for o in self.outputs:
            o.start()
        return True

    def stop_outputs(self):
        for o in self.outputs:
            o.stop()
        return True

    def delete_outputs(self):
        for o in self.outputs:
            o.delete()
        return True

    def delete(self):
        self.delete_outputs()
        self.server_connector.delete_device(self.rtmp_id)
        return True

    def select_server(self, server_id: Union[int, str]) -> SelectServerStatus:
        self._update_available_servers()
        if str(server_id) not in [s["id"] for s in self.available_servers]:
            raise Exception("Not allowed server_id")
        return self.server_connector.select_server(self.rtmp_id, server_id)

    def select_fastest_server(self) -> Optional[SelectServerStatus]:
        self._update_available_servers()
        if not self.available_servers:
            logger.warning("Failed to select server")
            return
        return self.server_connector.select_server(
            self.rtmp_id, self.available_servers[0]["id"]
        )
