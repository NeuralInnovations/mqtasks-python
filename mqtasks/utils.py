import json

from dataclasses import asdict, is_dataclass

from pydantic import BaseModel


def to_json_bytes(body: bytes | str | object | None = None) -> bytes | None:
    if body is None:
        return None

    data: bytes
    if body is not None:
        if isinstance(body, bytes):
            data = body
        elif isinstance(body, str):
            data = body.encode()
        elif isinstance(body, BaseModel):
            bm: BaseModel = body
            data = bm.json().encode()
        elif is_dataclass(body):
            data = json.dumps(asdict(body)).encode()
        else:
            data = json.dumps(body).encode()
    else:
        data = bytes()
    return data
