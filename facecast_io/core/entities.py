from typing import TypedDict, Literal, List


class DeviceSimple(TypedDict):
    rtmp_id: str
    name: str


class DeviceInput(TypedDict):
    server_url: str
    shared_key: str


class DeviceOutput(TypedDict):
    descr: str
    enabled: int
    type: Literal["rtmp_rtmp"]
    id: str
    cloud: int
    server_url: str


class DeviceOutputStatus(TypedDict):
    ok: bool
    outputs: List[DeviceOutput]
