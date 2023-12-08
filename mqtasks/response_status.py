from enum import Enum, StrEnum


class MqResponseStatus(StrEnum):
    SUCCESS: str = "success"
    FAILURE: str = "failure"

    @staticmethod
    def parse(value: str):
        if value == "success":
            return MqResponseStatus.SUCCESS
        if value == "failure":
            return MqResponseStatus.FAILURE
        raise ValueError(f"message {value} is not valid")
