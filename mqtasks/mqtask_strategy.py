from enum import Enum


class MqTasksConsumeStrategy(Enum):
    QUEUE = 1,
    PARALLEL = 2
