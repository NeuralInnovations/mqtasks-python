import uuid


class MqTaskIdFactory:
    def new_id(self) -> str:
        return str(uuid.uuid4())


class MqTaskMessageIdFactory:
    def new_id(self) -> str:
        return str(uuid.uuid4())
