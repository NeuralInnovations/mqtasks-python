from aio_pika.abc import AbstractRobustChannel, AbstractIncomingMessage

from mqtasks import MqTaskHeaders


class MqMessageContext:
    __channel: AbstractRobustChannel
    __message: AbstractIncomingMessage
    __wait_task: bool

    def __init__(
            self,
            channel: AbstractRobustChannel,
            message: AbstractIncomingMessage,
            wait_task: bool
    ):
        self.__message = message
        self.__channel = channel
        self.__wait_task = wait_task

    @property
    def wait_task(self):
        return self.__wait_task

    @property
    def channel(self):
        return self.__channel

    @property
    def message(self):
        return self.__message

    @property
    def task_id(self) -> str | None:
        return self.message.correlation_id

    @property
    def reply_to(self) -> str | None:
        return self.message.reply_to

    @property
    def message_id(self) -> str | None:
        return self.message.message_id

    @property
    def task_name(self):
        return self.message.headers[MqTaskHeaders.TASK]
