import asyncio
import logging

from example.example_config import CONNECTION, QUEUE_NANE_REQUEST_01, QUEUE_NANE_REQUEST_02, QUEUE_NANE_PUBLISH_01
from mqtasks import MqTasksClient

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("CLIENT")
logger.setLevel(logging.DEBUG)

loop = asyncio.get_event_loop()
client = MqTasksClient(
    loop=loop,
    amqp_connection=CONNECTION,
    logger=logger,
    verbose=True
)


async def exec_task_async(task_name: str, queue: str, body: str | object | None = None) -> None:
    channel = await client.queue(queue)
    return await channel.exec_task_async(
        task_name=task_name,
        body=body,
    )

async def request_task_async(task_name: str, queue: str, body: str | object | None = None) -> None:
    channel = await client.queue(queue)
    response = await channel.request_task_async(
        task_name=task_name,
        body=body,
        message_handler=lambda msg: print(msg)
    )
    print(response)


# ==============================================================================


loop.run_until_complete(request_task_async(task_name="hello_sync", queue=QUEUE_NANE_REQUEST_01, body={"message": "hello sync task1"}))
loop.run_until_complete(request_task_async(task_name="hello_async", queue=QUEUE_NANE_REQUEST_02, body={"message": "hello async task2"}))
loop.run_until_complete(asyncio.sleep(3))
loop.run_until_complete(request_task_async(task_name="hello_sync", queue=QUEUE_NANE_REQUEST_01, body={"message": "hello sync task3"}))
loop.run_until_complete(request_task_async(task_name="hello_async", queue=QUEUE_NANE_REQUEST_02, body={"message": "Привіт, перевірка килилиці"}))

loop.run_until_complete(
    request_task_async(task_name="data_async", queue=QUEUE_NANE_REQUEST_01, body={"message": "async progress task"}))

loop.run_until_complete(exec_task_async(task_name="task_async", queue=QUEUE_NANE_PUBLISH_01, body={"message": "publish_async"}))

loop.run_until_complete(request_task_async(task_name="no_task", queue=QUEUE_NANE_REQUEST_02, body={"message": "no_task"}))

loop.run_until_complete(client.close())

loop.close()
