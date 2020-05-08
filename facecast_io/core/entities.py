from typing import TypedDict, Literal, List, Dict, Union


class DeviceSimple(TypedDict):
    rtmp_id: str
    name: str


class DeviceInfo(TypedDict):
    rtmp_id: str
    online: bool
    type: Literal["rtmp_source"]
    lang: Literal["en", "ru"]
    updates: bool
    form_sign: str


class DeviceInput(TypedDict):
    rtmp_id: str
    server_url: str
    shared_key: str


class DeviceInputStatus(TypedDict, total=False):
    ok: bool
    msg: str
    resolution: str
    fps: str
    response: bool
    status: str
    time: float


class InputDeviceStatusSClient(TypedDict, total=False):
    id: str
    address: str
    time: str
    flashver: str
    swfurl: str
    dropped: str
    timestamp: str
    avsync: List
    active: List


class InputDeviceMetaAudio(TypedDict, total=False):
    codec: str
    profile: str
    channels: str
    sample_rate: str


class InputDeviceMetaVideo(TypedDict, total=False):
    width: str
    height: str
    frame_rate: str
    codec: str
    profile: str
    compat: str
    level: str


class InputDeviceMeta(TypedDict):
    video: InputDeviceMetaVideo
    audio: InputDeviceMetaAudio


class InputDeviceStatusS(TypedDict):
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


class DeviceStatus(TypedDict):
    ok: Literal[0, 1]
    server: str
    server_id: str
    is_online: Literal[0, 1]
    connected: Literal["0", "1"]
    s: InputDeviceStatusS
    input_url: str
    sharedkey: str
    ping: Literal[0, 1]
    time: float


class DeviceStatusFull(TypedDict, total=False):
    get_status: DeviceStatus
    input_status: DeviceInputStatus


class DeviceOutput(TypedDict):
    descr: str
    enabled: int
    type: Literal["rtmp_rtmp"]
    id: str
    cloud: int
    server_url: str


class DeviceOutputStatus(TypedDict, total=False):
    ok: bool
    msg: str
    outputs: List[DeviceOutput]


class SelectServer(TypedDict):
    id: str
    name: str


class SelectServerStatus(TypedDict):
    ok: bool
    server: SelectServer
    sharedkey: str


class OutputStatus(TypedDict):
    enabled: Literal[0, 1]


class OutputStatusStart(OutputStatus):
    ok: Literal[0, 1]
    msg: str
