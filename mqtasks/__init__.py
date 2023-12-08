import asyncio
from asyncio import AbstractEventLoop

from .body import MqTaskBody
from .channel import MqTasksChannel
from .client import MqTasksClient
from .context import MqTaskContext
from .headers import MqTaskHeaders
from .message import MqTaskMessage
from .message_id_factory import MqTaskMessageIdFactory
from .mqtasks import MqTasks
from .register import MqTaskRegister
from .response_types import MqTaskResponseTypes


def run_mqtasks(
        tasks: list[MqTasks],
        loop: AbstractEventLoop | None = None
):
    loop = loop if loop is not None else asyncio.get_event_loop()
    for task in tasks:
        loop.create_task(task.run_async(loop))
    loop.run_forever()
