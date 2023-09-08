import json


class MqTaskBody:
    body: bytes
    size: int

    def __init__(self, body: bytes, size: int):
        self.body = body
        self.size = size

    def as_string(self):
        return self.body.decode()

    def as_bytes(self):
        return self.body

    def as_json(self):
        return json.loads(self.body.decode())
