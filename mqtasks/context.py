import json
from asyncio import AbstractEventLoop
from logging import Logger
from typing import Optional

from aio_pika import Message
from aio_pika.abc import AbstractRobustChannel, AbstractRobustQueue, AbstractExchange
from aiormq.abc import ConfirmationFrameType

from mqtasks.body import MqTaskBody
from mqtasks.headers import MqTaskHeaders
from mqtasks.message_id_factory import MqTaskMessageIdFactory
from mqtasks.response_types import MqTaskResponseTypes


class MqTaskContext:
    channel: AbstractRobustChannel
    queue: AbstractRobustQueue
    exchange: AbstractExchange
    loop: AbstractEventLoop
    logger: Logger
    message_id_factory: MqTaskMessageIdFactory

    message_id: str
    name: str
    id: str
    relay_to: str
    body: MqTaskBody

    def __init__(
            self,
            logger: Logger,
            loop: AbstractEventLoop,
            channel: AbstractRobustChannel,
            queue: AbstractRobustQueue,
            exchange: AbstractExchange,
            message_id_factory: MqTaskMessageIdFactory,
            message_id: str,
            task_name: str,
            task_id: str,
            relay_to: str,
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
        self.relay_to = relay_to
        self.body = task_body

    async def publish_data_async(self, body: bytes | str | object) -> Optional[ConfirmationFrameType]:
        data: bytes
        if isinstance(body, bytes):
            data = body
        elif isinstance(body, str):
            data = body.encode()
        else:
            data = json.dumps(body).encode()

        return await self.exchange.publish(
            Message(
                headers={
                    MqTaskHeaders.TASK: self.name,
                    MqTaskHeaders.ID: self.id,
                    MqTaskHeaders.RESPONSE_TO_MESSAGE_ID: self.message_id,
                    MqTaskHeaders.RESPONSE_TYPE: MqTaskResponseTypes.DATA
                },
                message_id=self.message_id_factory.new_id(),
                body=data),
            routing_key=self.exchange.name,
        )
