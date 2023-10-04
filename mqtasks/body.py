import json
from typing import Any


class MqTaskBody:
    __json_cache: Any | None = None
    __string_cache: str | None = None
    __body: bytes
    __size: int

    def __init__(self, body: bytes, size: int):
        self.__body = body
        self.__size = size

    @property
    def body(self) -> bytes:
        return self.__body

    @property
    def size(self) -> int:
        return self.__size

    def as_string(self):
        if self.__string_cache is None:
            self.__string_cache = self.body.decode()
        return self.__string_cache

    @property
    def text(self) -> str:
        return self.as_string()

    def as_bytes(self):
        return self.body

    def as_json(self):
        if self.__json_cache is None:
            self.__json_cache = json.loads(self.as_string())
        return self.__json_cache

    @property
    def json(self) -> Any:
        return self.as_json()
