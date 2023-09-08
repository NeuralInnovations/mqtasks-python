import asyncio
import logging
from asyncio import AbstractEventLoop
from logging import Logger

import aio_pika
import aio_pika.abc
from aio_pika.abc import AbstractIncomingMessage, \
    ExchangeType

from mqtasks.body import MqTaskBody
from mqtasks.context import MqTaskContext
from mqtasks.headers import MqTaskHeaders
from mqtasks.message_id_factory import MqTaskMessageIdFactory
from mqtasks.register import MqTaskRegister


class MqTasks:
    __tasks = dict()
    __amqp_connection: str
    __queue_name: str
    __verbose: bool
    __loop: AbstractEventLoop
    __prefetch_count: int
    __message_id_factory: MqTaskMessageIdFactory

    def __init__(
            self,
            amqp_connection: str,
            queue_name: str,
            verbose: bool = False,
            prefetch_count: int = 1,
            logger: Logger | None = None,
            message_id_factory: MqTaskMessageIdFactory | None = None
    ):
        self.__amqp_connection = amqp_connection
        self.__queue_name = queue_name
        self.__verbose = verbose
        self.__prefetch_count = prefetch_count
        self.__logger = logger or logging.getLogger(f"{MqTasks.__name__}.{queue_name}")
        self.__message_id_factory = message_id_factory or MqTaskMessageIdFactory()

    async def __run_async(self, loop):
        connection = await aio_pika.connect_robust(
            self.__amqp_connection, loop=loop
        )
        async with connection:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=self.__prefetch_count)
            exchange = await channel.declare_exchange(
                name=self.__queue_name,
                type=ExchangeType.DIRECT,
                auto_delete=False
            )
            queue = await channel.declare_queue(self.__queue_name, auto_delete=False, durable=True)
            await queue.bind(exchange, self.__queue_name)
            async with queue.iterator() as queue_iter:
                message: AbstractIncomingMessage
                async for message in queue_iter:
                    async with message.process():
                        task_name = message.headers[MqTaskHeaders.TASK]
                        if task_name in self.__tasks:
                            register: MqTaskRegister = self.__tasks[task_name]
                            task_id = message.headers[MqTaskHeaders.ID]
                            relay_to = message.headers[MqTaskHeaders.RELAY_TO]
                            exchange = await channel.get_exchange(relay_to)
                            message_id = message.message_id

                            if self.__verbose:
                                self.__logger.debug(message.headers)
                                self.__logger.debug(message.body)

                            loop.create_task(register.invoke_async(
                                MqTaskContext(
                                    logger=self.__logger,
                                    loop=self.__loop,
                                    channel=channel,
                                    queue=queue,
                                    exchange=exchange,
                                    message_id_factory=self.__message_id_factory,
                                    message_id=message_id,
                                    task_name=task_name,
                                    task_id=task_id,
                                    relay_to=relay_to,
                                    task_body=MqTaskBody(
                                        body=message.body, size=message.body_size
                                    )),
                                verbose=self.__verbose
                            ))

    def task(
            self,
            name: str
    ):
        def func_decorator(func):
            self.__tasks[name] = MqTaskRegister(name=name, func=func)
            return func

        return func_decorator

    def loop(self):
        return self.__loop

    def run(self):
        self.__loop = asyncio.get_event_loop()
        self.__loop.run_until_complete(self.__run_async(self.__loop))
        self.__loop.close()
