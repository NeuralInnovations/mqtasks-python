import logging
from asyncio import AbstractEventLoop
from logging import Logger

import aio_pika
from aio_pika.abc import AbstractRobustConnection

from mqtasks.channel import MqTasksChannel
from mqtasks.message_id_factory import MqTaskMessageIdFactory, MqTaskIdFactory


class MqTasksClient:
    __amqp_connection: str
    __verbose: bool
    __loop: AbstractEventLoop
    __message_id_factory: MqTaskMessageIdFactory
    __task_id_factory: MqTaskIdFactory
    __connection: AbstractRobustConnection | None = None
    __logger: Logger

    def __init__(
            self,
            loop: AbstractEventLoop,
            amqp_connection: str,
            verbose: bool = False,
            logger: Logger | None = None,
            message_id_generator: MqTaskMessageIdFactory | None = None,
            task_id_factory: MqTaskIdFactory | None = None,
    ):
        self.__loop = loop
        self.__amqp_connection = amqp_connection
        self.__verbose = verbose
        self.__message_id_factory = message_id_generator or MqTaskMessageIdFactory()
        self.__task_id_factory = task_id_factory or MqTaskIdFactory()
        self.__logger = logger or logging.getLogger(f"{MqTasksClient.__name__}")

    @property
    def logger(self) -> Logger:
        return self.__logger

    async def close(self):
        if self.__connection is not None:
            await self.__connection.close()

    async def queue(
            self,
            queue_name: str,
    ) -> MqTasksChannel:
        connection: AbstractRobustConnection = self.__connection or await aio_pika.connect_robust(
            self.__amqp_connection,
            loop=self.__loop
        )
        self.__connection = connection

        client = MqTasksChannel(
            connection=connection,
            queue_name=queue_name,
            verbose=self.__verbose,
            loop=self.__loop,
            message_id_factory=self.__message_id_factory,
            logger=self.logger.getChild(queue_name),
            task_id_factory=self.__task_id_factory,
        )

        return client
