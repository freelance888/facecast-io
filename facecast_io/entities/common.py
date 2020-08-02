from typing import TypeVar, Generic, List, Optional

from pydantic import BaseModel, Field

__all__ = ["GenericList", "BaseResponse"]

from pydantic.generics import GenericModel

ListType = TypeVar("ListType")


class GenericList(GenericModel, Generic[ListType]):
    __root__: List[ListType]

    def __iter__(self) -> ListType:
        yield from self.__root__

    def __getitem__(self, item) -> ListType:
        return self.__root__[item]

    def __len__(self) -> int:
        return len(self.__root__)


class BaseResponse(BaseModel):
    ok: bool
    msg: Optional[str] = Field(alias="message")
