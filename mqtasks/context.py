from asyncio import AbstractEventLoop
from logging import Logger
from typing import Optional

from aio_pika import Message
from aio_pika.abc import AbstractRobustChannel, AbstractExchange, AbstractQueue
from aiormq.abc import ConfirmationFrameType

from mqtasks.body import MqTaskBody
from mqtasks.headers import MqTaskHeaders
from mqtasks.message_id_factory import MqTaskMessageIdFactory
from mqtasks.response_types import MqTaskResponseTypes
from mqtasks.utils import to_json_bytes


class MqTaskContext:
    channel: AbstractRobustChannel
    queue: AbstractQueue
    exchange: AbstractExchange
    loop: AbstractEventLoop
    logger: Logger
    message_id_factory: MqTaskMessageIdFactory

    message_id: str
    name: str
    id: str
    reply_to: str
    body: MqTaskBody

    def __init__(
            self,
            logger: Logger,
            loop: AbstractEventLoop,
            channel: AbstractRobustChannel,
            queue: AbstractQueue | None,
            exchange: AbstractExchange | None,
            message_id_factory: MqTaskMessageIdFactory,
            message_id: str,
            task_name: str,
            task_id: str,
            reply_to: str,
            task_body: MqTaskBody
    ):
        self.logger = logger
        self.loop = loop
        self.queue = queue
        self.channel = channel
        self.exchange = exchange
        self.message_id_factory = message_id_factory
        self.message_id = message_id
        self.name = task_name
        self.id = task_id
        self.reply_to = reply_to
        self.body = task_body

    async def publish_data_async(
            self,
            body: bytes | str | object | None = None,
    ) -> Optional[ConfirmationFrameType]:
        data: bytes = to_json_bytes(body)

        return await self.exchange.publish(
            Message(
                headers={
                    MqTaskHeaders.TASK: self.name,
                    MqTaskHeaders.RESPONSE_TO_MESSAGE_ID: self.message_id,
                    MqTaskHeaders.RESPONSE_TYPE: MqTaskResponseTypes.DATA
                },
                correlation_id=self.id,
                message_id=self.message_id_factory.new_id(),
                body=data),
            routing_key=self.exchange.name,
        )
