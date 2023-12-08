from asyncio import AbstractEventLoop
from logging import Logger
from typing import Callable

import aio_pika
from aio_pika import ExchangeType
from aio_pika.abc import AbstractRobustConnection, AbstractRobustChannel, AbstractIncomingMessage

from mqtasks.body import MqTaskBody
from mqtasks.headers import MqTaskHeaders
from mqtasks.message import MqTaskMessage
from mqtasks.message_id_factory import MqTaskMessageIdFactory, MqTaskIdFactory
from mqtasks.response_status import MqResponseStatus
from mqtasks.response_types import MqTaskResponseTypes
from mqtasks.utils import to_json_bytes


class MqTasksChannel:
    __connection: AbstractRobustConnection
    __queue_name: str
    __verbose: bool
    __loop: AbstractEventLoop
    __message_id_factory: MqTaskMessageIdFactory
    __task_id_factory: MqTaskIdFactory
    __logger: Logger

    def __init__(
            self,
            connection: AbstractRobustConnection,
            queue_name: str,
            verbose: bool,
            loop: AbstractEventLoop,
            message_id_factory: MqTaskMessageIdFactory,
            logger: Logger,
            task_id_factory: MqTaskIdFactory,
    ):
        self.__connection = connection
        self.__queue_name = queue_name
        self.__verbose = verbose
        self.__loop = loop
        self.__message_id_factory = message_id_factory
        self.__logger = logger
        self.__task_id_factory = task_id_factory

    @property
    def channel(self) -> AbstractRobustChannel:
        return self.__connection.channel()

    @property
    def logger(self) -> Logger:
        return self.__logger

    async def run_task_async(
            self,
            task_name: str,
            task_id: str | None = None,
            body: bytes | str | object | None = None,
            message_handler: Callable[[MqTaskMessage], None] | None = None,
    ) -> MqTaskMessage:
        data: bytes = to_json_bytes(body)

        # async with self.__connection:
        routing_key = self.__queue_name
        channel = await self.__connection.channel()

        message_id = self.__message_id_factory.new_id()
        task_id = task_id or self.__task_id_factory.new_id()
        task_replay_to = f"replay.{task_name}.{task_id}"

        # ------------------------------------------------------------
        # get queue and exchange to request
        task_queue = await channel.get_queue(name=routing_key)
        task_exchange = await channel.get_exchange(name=routing_key)

        # ------------------------------------------------------------
        # declare queue and exchange to response
        response_queue = await channel.declare_queue(name=task_replay_to, durable=True)
        response_exchange = await channel.declare_exchange(name=task_replay_to, type=ExchangeType.DIRECT, durable=True)
        # bind queue to exchange
        await response_queue.bind(response_exchange)

        # we send message to do the task
        await task_exchange.publish(
            aio_pika.Message(
                headers={
                    MqTaskHeaders.TASK: task_name,
                },
                correlation_id=task_id,
                reply_to=task_replay_to,
                message_id=message_id,
                body=data),
            routing_key=routing_key,
        )

        response: MqTaskMessage
        # we will receive response of task
        async with response_queue.iterator() as queue_iter:
            message: AbstractIncomingMessage
            async for message in queue_iter:
                async with message.process():
                    if message.headers[MqTaskHeaders.RESPONSE_TYPE] == MqTaskResponseTypes.DATA:
                        if message_handler is not None:
                            message_handler(
                                MqTaskMessage(
                                    logger=self.logger,
                                    loop=self.__loop,
                                    message_id=message.message_id,
                                    task_name=message.headers[MqTaskHeaders.TASK],
                                    task_id=message.correlation_id,
                                    task_body=MqTaskBody(
                                        body=message.body, size=message.body_size
                                    ),
                                    status=MqResponseStatus.parse(message.headers[MqTaskHeaders.RESPONSE_STATUS]),
                                ))
                    elif message.headers[MqTaskHeaders.RESPONSE_TYPE] == MqTaskResponseTypes.RESPONSE:
                        response = MqTaskMessage(
                            logger=self.logger,
                            loop=self.__loop,
                            message_id=message.message_id,
                            task_name=message.headers[MqTaskHeaders.TASK],
                            task_id=message.correlation_id,
                            task_body=MqTaskBody(
                                body=message.body, size=message.body_size
                            ),
                            status=MqResponseStatus.parse(message.headers[MqTaskHeaders.RESPONSE_STATUS]),
                        )
                        break

        await response_queue.unbind(response_exchange)
        await response_queue.delete()
        await response_exchange.delete()
        await channel.close()

        return response
