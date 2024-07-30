import asyncio
import logging
from asyncio import AbstractEventLoop
from logging import Logger
from typing import Callable, Any, Coroutine

import aio_pika
import aio_pika.abc
from aio_pika.abc import (
    AbstractIncomingMessage,
    ExchangeType,
    AbstractExchange,
    AbstractQueue,
    AbstractRobustConnection,
    ConsumerTag,
    AbstractRobustChannel,
    AbstractRobustQueue, AbstractRobustExchange,
)

from mqtasks.body import MqTaskBody
from mqtasks.context import MqTaskContext
from mqtasks.message_id_factory import MqTaskMessageIdFactory
from mqtasks.mqtasks_message_context import MqMessageContext
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
    __middlewares: list[Callable[[MqMessageContext, Callable[[MqMessageContext], Any]], Any]] = []
    __message_queue: list[AbstractIncomingMessage] = []
    __consumer_tag: ConsumerTag | None = None
    __middleware_chain: Callable[[Any], Coroutine[Any, Any, None]] | None = None
    __is_terminated: bool = False

    __queue: AbstractRobustQueue
    __exchange: AbstractRobustExchange
    __channel: AbstractRobustChannel

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
        self.__middlewares = []
        self.__message_queue = []
        self.__middleware_chain = None

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

    async def __process_message(
            self,
            context: MqMessageContext
    ):
        channel: AbstractRobustChannel = context.channel
        message: AbstractIncomingMessage = context.message
        wait_task: bool = context.wait_task

        task_name = context.task_name
        if task_name in self.__tasks:
            register: MqTaskRegister = self.__tasks[task_name]
            task_id: str | None = context.task_id
            reply_to: str | None = context.reply_to
            message_id: str | None = context.message_id

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

            invoke_task = self.loop.create_task(register.invoke_async(
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

            if self.__wait_invoke_task or wait_task:
                await invoke_task

    def __build_middleware_chain(
            self,
            middlewares: list[Callable[[MqMessageContext, Callable[[MqMessageContext], Any]], Any]],
            final_handler: Callable[[MqMessageContext], Any]
    ):
        async def next_middleware(message, index):
            if index < len(middlewares):
                await middlewares[index](message, lambda msg: next_middleware(msg, index + 1))
            else:
                await final_handler(message)

        return lambda message: next_middleware(message, 0)

    async def __consume(self, message: AbstractIncomingMessage):
        if self.__if_log:
            self.__log(f"Consuming, message: {message}")

        await self.__stop_consume()
        async with message.process():
            self.__message_queue.append(message)
            await self.__process_message(MqMessageContext(
                channel=self.__channel,
                message=message,
                wait_task=False
            ))
            self.__message_queue.remove(message)
        await self.__start_consume()

    async def __start_consume(self):
        if self.__if_log:
            self.__log(f"Starting consuming")

        try:
            queue: AbstractRobustQueue = self.__queue
            self.__consumer_tag = await queue.consume(callback=self.__consume, no_ack=False)
        except Exception as e:
            if self.__if_log:
                self.__log(f"Exception:{e}")

    async def __stop_consume(self):
        if self.__if_log:
            self.__log(f"Stopping consuming")

        tag: ConsumerTag | None = self.__consumer_tag
        self.__consumer_tag = None
        await self.__queue.cancel(tag)

    async def __start_connection(self, loop: AbstractEventLoop | None):
        if self.__if_log:
            self.__log(f"aio_pika.connect_robust->begin connection:{self.__amqp_connection}")
        connection: AbstractRobustConnection = await aio_pika.connect_robust(
            self.__amqp_connection,
            loop=loop
        )
        if self.__if_log:
            self.__log(f"aio_pika.connect_robust->end connection:{self.__amqp_connection}")
            self.__log_line()

        async with connection:

            if self.__if_log:
                self.__log("connection.channel()->begin")
            channel: AbstractRobustChannel = await connection.channel()
            self.__channel = channel
            if self.__if_log:
                self.__log("connection.channel()->end")
                self.__log_line()

            await channel.set_qos(prefetch_count=self.__prefetch_count)

            if self.__if_log:
                self.__log(f"channel.declare_exchange->begin exchange:{self.__queue_name}")
            exchange: AbstractRobustExchange = await channel.declare_exchange(
                name=self.__queue_name,
                type=ExchangeType.DIRECT,
                durable=True,
                auto_delete=False
            )
            self.__exchange = exchange
            if self.__if_log:
                self.__log(f"channel.declare_exchange->end exchange:{self.__queue_name}")
                self.__log_line()

            if self.__if_log:
                self.__log(f"channel.declare_queue->begin queue:{self.__queue_name}")
            queue: AbstractRobustQueue = await channel.declare_queue(
                self.__queue_name,
                auto_delete=False,
                durable=True
            )
            self.__queue = queue
            if self.__if_log:
                self.__log(f"channel.declare_queue->end queue:{self.__queue_name}")
                self.__log_line()

            if self.__if_log:
                self.__log(f"queue.bind->begin queue:{self.__queue_name}")
            await queue.bind(exchange, self.__queue_name)
            if self.__if_log:
                self.__log(f"queue.bind->end queue:{self.__queue_name}")
                self.__log_line()

            if len(self.__message_queue) != 0:
                if self.__if_log:
                    self.__log(f"restore messages from queue, count:{len(self.__message_queue)}")
                while len(self.__message_queue) != 0:
                    msg: AbstractIncomingMessage = self.__message_queue[0]
                    await self.__process_message(
                        context=MqMessageContext(
                            channel=channel,
                            message=msg,
                            wait_task=True
                        )
                    )
                    self.__message_queue.pop(0)

            await self.__start_consume()

            while not connection.is_closed and not self.__is_terminated:
                await asyncio.sleep(1)

            if self.__if_log:
                self.__log(f"Connection is closed")

    async def __run_async(self, loop: AbstractEventLoop | None):
        self.__middleware_chain = self.__build_middleware_chain(
            middlewares=self.__middlewares,
            final_handler=self.__process_message
        )
        while self.__is_terminated is False:
            try:
                await self.__start_connection(loop=loop)
            except Exception as e:
                if self.__if_log:
                    self.__log(f"Exception:{e}")
            await asyncio.sleep(2)
            if self.__if_log:
                self.__log("Reconnecting")

    def task(
            self,
            name: str
    ):
        def func_decorator(func):
            self.__tasks[name] = MqTaskRegister(name=name, func=func)
            return func

        return func_decorator

    def middleware(
            self,
            middleware: Callable[[MqMessageContext, Callable[[MqMessageContext], Any]], Any]
    ):
        self.__middlewares.append(middleware)

    @property
    def loop(self):
        return self.__loop

    def run(self, event_loop: AbstractEventLoop | None = None):
        self.__loop = event_loop or asyncio.get_event_loop()
        self.__loop.run_until_complete(self.__run_async(self.__loop))
        self.__loop.run_forever()

    async def run_async(self, event_loop: AbstractEventLoop | None = None):
        self.__loop = event_loop or asyncio.get_event_loop()
        await self.__run_async(loop=self.__loop)

    def terminate(self):
        self.__is_terminated = True
