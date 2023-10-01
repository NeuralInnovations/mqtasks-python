import json

from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class JSON:
    @staticmethod
    def __serializer(value: Any):
        if isinstance(value, datetime):
            return value.isoformat()
        return JSON.dumps(value)

    @staticmethod
    def loads(value: str | None):
        return json.loads(value)

    @staticmethod
    def dumps(value: Any) -> str | None:
        data: str | None = None
        if value is not None:
            if isinstance(value, BaseModel):
                bm: BaseModel = value
                data = bm.json()
            elif is_dataclass(value):
                data = json.dumps(asdict(value), default=JSON.__serializer)
            else:
                data = json.dumps(value, default=JSON.__serializer)
        return data


def to_json_bytes(body: bytes | str | object | None = None) -> bytes | None:
    if body is None:
        return None

    data: bytes
    if body is not None:
        if isinstance(body, bytes):
            data = body
        elif isinstance(body, str):
            data = body.encode()
        else:
            data = JSON.dumps(body).encode()
    else:
        data = bytes()
    return data
