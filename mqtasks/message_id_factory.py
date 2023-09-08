import uuid


class MqTaskMessageIdFactory:
    def new_id(self) -> str:
        return str(uuid.uuid4())
