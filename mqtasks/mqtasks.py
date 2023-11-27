import asyncio
import logging
from asyncio import AbstractEventLoop
from logging import Logger

import aio_pika
import aio_pika.abc
from aio_pika.abc import (
    AbstractIncomingMessage,
    ExchangeType,
    AbstractExchange,
    AbstractQueue,
    AbstractRobustConnection,
)

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
    __wait_invoke_task: bool = False

    def __init__(
            self,
            amqp_connection: str,
            queue_name: str,
            prefetch_count: int = 1,
            logger: Logger | None = None,
            message_id_factory: MqTaskMessageIdFactory | None = None,
            logging_level: int = logging.INFO,
            wait_invoke_task: bool = False,
    ):
        self.__amqp_connection = amqp_connection
        self.__queue_name = queue_name
        self.__prefetch_count = prefetch_count
        self.__logger = logger
        self.__message_id_factory = message_id_factory or MqTaskMessageIdFactory()
        self.__logging_level = logging_level
        self.__wait_invoke_task = wait_invoke_task

        if self.__logger is None:
            self.__logger = logging.getLogger(f"{MqTasks.__name__}.{queue_name}")
            self.__logger.setLevel(logging_level)

    @property
    def __if_log(self):
        return self.__logger.isEnabledFor(self.__logging_level)

    def __log(self, msg):
        self.__logger.log(self.__logging_level, msg)

    def __log_line(self):
        self.__logger.log(self.__logging_level, "------------------------------")

    async def __run_async(self, loop):
        connection: AbstractRobustConnection | None = None
        message_queue: list[AbstractIncomingMessage] = []
        is_work = True

        while is_work:
            try:
                if self.__if_log:
                    self.__log(f"aio_pika.connect_robust->begin connection:{self.__amqp_connection}")
                connection = await aio_pika.connect_robust(
                    self.__amqp_connection,
                    loop=loop
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

                    def consume(msg: AbstractIncomingMessage):
                        pass

                    await queue.consume(callback=consume, no_ack=False)

                    async def process_message(message: AbstractIncomingMessage):
                        task_name = message.headers[MqTaskHeaders.TASK]
                        if task_name in self.__tasks:
                            register: MqTaskRegister = self.__tasks[task_name]
                            task_id: str | None = message.correlation_id
                            reply_to: str | None = message.reply_to
                            message_id: str | None = message.message_id

                            reply_to_exchange: AbstractExchange | None = None
                            reply_to_queue: AbstractQueue | None = None
                            if reply_to is not None and reply_to != "":
                                reply_to_exchange = await channel.declare_exchange(
                                    name=reply_to,
                                    durable=True,
                                    type=ExchangeType.DIRECT,
                                    auto_delete=False
                                )
                                reply_to_queue = await channel.declare_queue(
                                    name=reply_to,
                                    durable=True
                                )

                            if self.__if_log:
                                self.__log(f"task {task_name}")
                                self.__log(message.headers)
                                self.__log(message.body)
                                self.__log_line()

                            invoke_task = loop.create_task(register.invoke_async(
                                MqTaskContext(
                                    logger=self.__logger,
                                    loop=self.__loop,
                                    channel=channel,
                                    queue=reply_to_queue,
                                    exchange=reply_to_exchange,
                                    routing_key=reply_to,
                                    message_id_factory=self.__message_id_factory,
                                    message_id=message_id,
                                    task_name=task_name,
                                    task_id=task_id,
                                    reply_to=reply_to,
                                    task_body=MqTaskBody(
                                        body=message.body, size=message.body_size
                                    )),
                            ))

                            if self.__wait_invoke_task:
                                await invoke_task

                    while len(message_queue) != 0:
                        msg = message_queue[0]
                        await process_message(msg)
                        message_queue.pop(0)

                    async with queue.iterator() as queue_iter:
                        message: AbstractIncomingMessage
                        async for message in queue_iter:
                            async with message.process():
                                message_queue.append(message)
                                await process_message(message)
                                message_queue.pop(0)

            except Exception as exc:
                self.__logger.exception(exc)
                try:
                    if connection is not None:
                        await connection.close()
                except Exception as c_exc:
                    self.__logger.exception(c_exc)
                    pass

                await asyncio.sleep(1)

    def task(
            self,
            name: str
    ):
        def func_decorator(func):
            self.__tasks[name] = MqTaskRegister(name=name, func=func)
            return func

        return func_decorator

    @property
    def loop(self):
        return self.__loop

    def run(self, event_loop: AbstractEventLoop | None = None):
        self.__loop = event_loop or asyncio.get_event_loop()
        self.__loop.run_until_complete(self.__run_async(self.__loop))
        self.__loop.close()
