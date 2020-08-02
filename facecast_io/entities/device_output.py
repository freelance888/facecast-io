try:
    from typing import Literal, Optional
except ImportError:
    from typing_extensions import Literal  # type: ignore

from typing import List

from pydantic import BaseModel, Field

from .common import GenericList, BaseResponse

__all__ = [
    "DeviceOutput",
    "DeviceOutputs",
    "DeviceOutputStatus",
    "OutputStatus",
    "OutputStatusStart",
]


class DeviceOutput(BaseModel):
    title: str = Field(alias="descr")
    enabled: int
    type: Literal["rtmp_rtmp"]
    id: str
    cloud: int
    server_url: str


class DeviceOutputs(GenericList[DeviceOutput]):
    ...


class DeviceOutputStatus(BaseResponse):
    outputs: List[DeviceOutput]


class OutputStatus(BaseModel):
    enabled: bool


class OutputStatusStart(BaseResponse, OutputStatus):
    ok: Optional[bool]
