from asyncio import AbstractEventLoop
from logging import Logger
from typing import Optional

from aio_pika import Message
from aio_pika.abc import AbstractRobustChannel, AbstractExchange, AbstractQueue
from aiormq.abc import ConfirmationFrameType

from mqtasks.body import MqTaskBody
from mqtasks.headers import MqTaskHeaders
from mqtasks.message_id_factory import MqTaskMessageIdFactory
from mqtasks.response_status import MqResponseStatus
from mqtasks.response_types import MqTaskResponseTypes
from mqtasks.utils import to_json_bytes


class MqTaskContext:
    _channel: AbstractRobustChannel
    _queue: AbstractQueue | None
    _exchange: AbstractExchange | None
    _routing_key: str | None
    _loop: AbstractEventLoop
    _logger: Logger
    _message_id_factory: MqTaskMessageIdFactory

    _message_id: str
    _name: str
    _id: str
    _reply_to: str | None
    _body: MqTaskBody

    def __init__(
            self,
            logger: Logger,
            loop: AbstractEventLoop,
            channel: AbstractRobustChannel,
            queue: AbstractQueue | None,
            exchange: AbstractExchange | None,
            routing_key: str | None,
            message_id_factory: MqTaskMessageIdFactory,
            message_id: str,
            task_name: str,
            task_id: str,
            reply_to: str | None,
            task_body: MqTaskBody
    ):
        self._logger = logger
        self._loop = loop
        self._queue = queue
        self._channel = channel
        self._exchange = exchange
        self._routing_key = routing_key
        self._message_id_factory = message_id_factory
        self._message_id = message_id
        self._name = task_name
        self._id = task_id
        self._reply_to = reply_to
        self._body = task_body

    @property
    def logger(self) -> Logger:
        return self._logger

    @property
    def loop(self) -> AbstractEventLoop:
        return self._loop

    @property
    def message_id(self) -> str:
        return self._message_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def id(self) -> str:
        return self._id

    @property
    def reply_to(self) -> str | None:
        return self._reply_to

    @property
    def body(self) -> MqTaskBody:
        return self._body

    @property
    def message_id_factory(self) -> MqTaskMessageIdFactory:
        return self._message_id_factory

    @property
    def routing_key(self) -> str | None:
        return self._routing_key

    @property
    def exchange(self) -> AbstractExchange | None:
        return self._exchange

    @property
    def is_request(self) -> bool:
        return self._exchange is not None and self._reply_to is not None

    async def publish_data_async(
            self,
            body: bytes | str | object | None = None,
    ) -> Optional[ConfirmationFrameType]:
        if not self.is_request:
            raise Exception(
                f"Task {self.name}, id:{self.id}, message_id:{self.message_id}. It is not a request, so you can't publish data as response")

        data: bytes = to_json_bytes(body)

        return await self._exchange.publish(
            Message(
                headers={
                    MqTaskHeaders.TASK: self._name,
                    MqTaskHeaders.RESPONSE_TO_MESSAGE_ID: self._message_id,
                    MqTaskHeaders.RESPONSE_TYPE: MqTaskResponseTypes.DATA,
                    MqTaskHeaders.RESPONSE_STATUS: MqResponseStatus.SUCCESS
                },
                correlation_id=self._id,
                message_id=self._message_id_factory.new_id(),
                body=data
            ),
            routing_key=self._routing_key,
        )
