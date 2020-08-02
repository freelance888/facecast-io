from pydantic import BaseModel

__all__ = ["BaseStream", "Stream"]


class BaseStream(BaseModel):
    server_url: str
    shared_key: str


class Stream(BaseStream):
    name: str
