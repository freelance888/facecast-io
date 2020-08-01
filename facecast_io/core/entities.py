from typing import List, Optional, Generic, TypeVar

from pydantic import BaseModel, Field

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal  # type: ignore


class DeviceSimple(BaseModel):
    rtmp_id: str
    name: str


class DeviceInfo(BaseModel):
    rtmp_id: str
    online: bool
    type: Literal["rtmp_source"]
    lang: Literal["en", "ru"]
    updates: bool
    form_sign: str


class DeviceInput(BaseModel):
    rtmp_id: str
    server_url: str
    shared_key: str


class DeviceServerSignal(BaseModel):
    msg: str
    ok: bool
    resolution: Optional[str]
    fps: Optional[bool]
    response: Optional[bool]
    status: Optional[str]

    @property
    def is_connected(self):
        return self.fps and self.resolution


class DeviceInputStatus(BaseModel):
    main: DeviceServerSignal
    backup: DeviceServerSignal
    time: float


class InputDeviceStatusSClient(BaseModel):
    id: str
    address: str
    time: str
    flashver: str
    swfurl: str
    dropped: str
    timestamp: str
    avsync: List
    active: List


class InputDeviceMetaAudio(BaseModel):
    codec: str
    profile: str
    channels: str
    sample_rate: str


class InputDeviceMetaVideo(BaseModel):
    width: str
    height: str
    frame_rate: str
    codec: str
    profile: str
    compat: str
    level: str


class InputDeviceMeta(BaseModel):
    video: InputDeviceMetaVideo
    audio: InputDeviceMetaAudio


class InputDeviceStatusS(BaseModel):
    name: str
    time: str
    bw_in: str
    bytes_in: str
    bw_out: str
    bytes_out: str
    bw_audio: str
    bw_video: str
    client: List[InputDeviceStatusSClient]
    meta: InputDeviceMeta
    nclients: str
    publishing: List
    active: List


class BackupServer(BaseModel):
    selected: bool
    server_id: str
    server_name: str
    input_signal: bool


class DeviceStatus(BaseModel):
    ok: Literal[0, 1]
    server: str
    server_id: str
    is_online: Literal[0, 1]
    connected: Literal["0", "1"]
    backup_server: BackupServer
    s: Optional[InputDeviceStatusS]
    input_url: str
    sharedkey: str
    ping: Literal[0, 1]
    time: float


class DeviceStatusFull(BaseModel):
    get_status: DeviceStatus
    input_status: Optional[DeviceInputStatus]


class DeviceOutput(BaseModel):
    descr: str
    enabled: int
    type: Literal["rtmp_rtmp"]
    id: str
    cloud: int
    server_url: str


ListType = TypeVar("ListType")


class GenericList(Generic[ListType], BaseModel):
    __root__: List[ListType]

    def __iter__(self) -> ListType:
        yield from self.__root__

    def __getitem__(self, item) -> ListType:
        return self.__root__[item]

    def __len__(self) -> int:
        return len(self.__root__)


class DeviceOutputs(GenericList[DeviceOutput]):
    ...


class DeviceOutputStatus(BaseModel):
    ok: bool
    msg: Optional[str]
    outputs: List[DeviceOutput]


class SelectServer(BaseModel):
    id: str
    name: str


class SelectServerStatus(BaseModel):
    ok: bool
    server: SelectServer
    sharedkey: str


class OutputStatus(BaseModel):
    enabled: Literal[0, 1]


class OutputStatusStart(OutputStatus):
    ok: Literal[0, 1]
    msg: str


class Stream(BaseModel):
    name: str
    server_url: str
    shared_key: str
