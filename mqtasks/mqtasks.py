import asyncio
import logging
from asyncio import AbstractEventLoop
from logging import Logger

import aio_pika
import aio_pika.abc
from aio_pika.abc import AbstractIncomingMessage, \
    ExchangeType, \
    AbstractExchange, \
    AbstractQueue

from mqtasks.body import MqTaskBody
from mqtasks.context import MqTaskContext
from mqtasks.headers import MqTaskHeaders
from mqtasks.message_id_factory import MqTaskMessageIdFactory
from mqtasks.register import MqTaskRegister


class MqTasks:
    __tasks = dict()
    __amqp_connection: str
    __queue_name: str
    __loop: AbstractEventLoop
    __prefetch_count: int
    __message_id_factory: MqTaskMessageIdFactory
    __logging_level: int

    def __init__(
            self,
            amqp_connection: str,
            queue_name: str,
            prefetch_count: int = 1,
            logger: Logger | None = None,
            message_id_factory: MqTaskMessageIdFactory | None = None,
            logging_level: int = logging.INFO,
    ):
        self.__amqp_connection = amqp_connection
        self.__queue_name = queue_name
        self.__prefetch_count = prefetch_count
        self.__logger = logger or logging.getLogger(f"{MqTasks.__name__}.{queue_name}")
        self.__message_id_factory = message_id_factory or MqTaskMessageIdFactory()
        self.__logging_level = logging_level

    @property
    def __if_log(self):
        return self.__logger.isEnabledFor(self.__logging_level)

    def __log(self, msg):
        self.__logger.log(self.__logging_level, msg)

    def __log_line(self):
        self.__logger.log(self.__logging_level, "------------------------------")

    async def __run_async(self, loop):
        if self.__if_log:
            self.__log(f"aio_pika.connect_robust->begin connection:{self.__amqp_connection}")
        connection = await aio_pika.connect_robust(
            self.__amqp_connection, loop=loop
        )
        if self.__if_log:
            self.__log(f"aio_pika.connect_robust->end connection:{self.__amqp_connection}")
            self.__log_line()

        async with connection:

            if self.__if_log:
                self.__log("connection.channel()->begin")
            channel = await connection.channel()
            if self.__if_log:
                self.__log("connection.channel()->end")
                self.__log_line()

            await channel.set_qos(prefetch_count=self.__prefetch_count)

            if self.__if_log:
                self.__log(f"channel.declare_exchange->begin exchange:{self.__queue_name}")
            exchange = await channel.declare_exchange(
                name=self.__queue_name,
                type=ExchangeType.DIRECT,
                durable=True,
                auto_delete=False
            )
            if self.__if_log:
                self.__log(f"channel.declare_exchange->end exchange:{self.__queue_name}")
                self.__log_line()

            if self.__if_log:
                self.__log(f"channel.declare_queue->begin queue:{self.__queue_name}")
            queue = await channel.declare_queue(self.__queue_name, auto_delete=False, durable=True)
            if self.__if_log:
                self.__log(f"channel.declare_queue->end queue:{self.__queue_name}")
                self.__log_line()

            if self.__if_log:
                self.__log(f"queue.bind->begin queue:{self.__queue_name}")
            await queue.bind(exchange, self.__queue_name)
            if self.__if_log:
                self.__log(f"queue.bind->end queue:{self.__queue_name}")
                self.__log_line()

            async with queue.iterator() as queue_iter:
                message: AbstractIncomingMessage
                async for message in queue_iter:
                    async with message.process():
                        task_name = message.headers[MqTaskHeaders.TASK]
                        if task_name in self.__tasks:
                            register: MqTaskRegister = self.__tasks[task_name]
                            task_id = message.correlation_id
                            reply_to = message.reply_to
                            message_id = message.message_id

                            reply_to_exchange: AbstractExchange | None = None
                            reply_to_queue: AbstractQueue | None = None
                            if reply_to is not None or reply_to != "":
                                reply_to_exchange = await channel.get_exchange(reply_to)
                                reply_to_queue = await channel.get_queue(reply_to)

                            if self.__if_log:
                                self.__log(f"task {task_name}")
                                self.__log(message.headers)
                                self.__log(message.body)
                                self.__log_line()

                            loop.create_task(register.invoke_async(
                                MqTaskContext(
                                    logger=self.__logger,
                                    loop=self.__loop,
                                    channel=channel,
                                    queue=reply_to_queue,
                                    exchange=reply_to_exchange,
                                    message_id_factory=self.__message_id_factory,
                                    message_id=message_id,
                                    task_name=task_name,
                                    task_id=task_id,
                                    reply_to=reply_to,
                                    task_body=MqTaskBody(
                                        body=message.body, size=message.body_size
                                    )),
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

    def run(self, event_loop=None):
        self.__loop = event_loop or asyncio.get_event_loop()
        self.__loop.run_until_complete(self.__run_async(self.__loop))
        self.__loop.close()
