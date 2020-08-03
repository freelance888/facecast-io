try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal  # type: ignore

from typing import Optional

from pydantic import BaseModel, Field

from .common import GenericList, BaseResponse
from .device_input import InputDeviceStatusS, DeviceInputStatus

__all__ = [
    "DeviceStatusFull",
    "BaseDevice",
    "BaseDevices",
    "DeviceInfo",
    "SelectServer",
    "SelectServerStatus",
    "AvailableServers",
    "DeviceStatus",
]


class BaseDevice(BaseModel):
    rtmp_id: int
    name: str


class BaseDevices(GenericList[BaseDevice]):
    ...


class DeviceInfo(BaseModel):
    rtmp_id: int
    online: bool
    type: Literal["rtmp_source"]
    lang: Literal["en", "ru"]
    updates: bool
    form_sign: str


class BackupServer(BaseModel):
    selected: bool
    server_id: int
    server_name: str
    input_signal: bool


class DeviceStatus(BaseResponse):
    server_name: str = Field(alias="server")
    server_id: int
    is_online: bool
    connected: bool
    backup_server: BackupServer
    s: Optional[InputDeviceStatusS]
    input_url: str
    shared_key: str = Field(alias="sharedkey")
    ping: bool
    time: float


class DeviceStatusFull(BaseModel):
    status: DeviceStatus = Field(alias="get_status")
    input: Optional[DeviceInputStatus] = Field(alias="input_status")

    @property
    def is_online(self) -> bool:
        return self.status.is_online

    @property
    def main_server_id(self) -> int:
        return self.status.server_id

    @property
    def backup_server_id(self) -> int:
        return self.status.backup_server.server_id

    @property
    def main_server_url(self) -> str:
        return self.status.input_url

    @property
    def shared_key(self) -> str:
        return self.status.shared_key


class Location(BaseModel):
    lat: float
    long: float


class SelectServer(BaseModel):
    id: int
    name: str
    url: str
    geo: Location
    can_connect: bool
    connected: Optional[bool]
    is_backup: Optional[bool]


class SelectServerStatus(BaseResponse):
    server: SelectServer
    shared_key: str = Field(alias="sharedkey")


class SelectedServer(BaseModel):
    id: int
    name: Optional[str]


class AvailableServers(GenericList[SelectServer]):
    @property
    def fastest(self):
        return self.__root__[0]

    def __getitem__(self, item: int) -> SelectServer:
        try:
            return [s for s in self.__root__ if s.id == item][0]
        except IndexError:
            raise ValueError(f"Not available server with id {item}")

    def __contains__(self, item: str) -> bool:
        return item in [s.id for s in self.__root__]
