from typing import Optional, List

from pydantic import BaseModel

from .common import BaseResponse


class DeviceServerSignal(BaseResponse):
    resolution: Optional[str]
    fps: Optional[bool]
    response: Optional[bool]
    status: Optional[str]


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
