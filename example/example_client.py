import asyncio
import logging

from example.example_config import CONNECTION, QUEUE_NANE_01, QUEUE_NANE_02
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


async def main_async(task_name: str, queue: str, body: str | object | None = None) -> None:
    channel = await client.queue(queue)
    response = await channel.run_task_async(
        task_name=task_name,
        body=body,
        message_handler=lambda msg: print(msg)
    )
    print(response)


# ==============================================================================


loop.run_until_complete(main_async(task_name="hello_sync", queue=QUEUE_NANE_01, body={"message": "hello sync task1"}))
loop.run_until_complete(main_async(task_name="hello_async", queue=QUEUE_NANE_02, body={"message": "hello async task2"}))
loop.run_until_complete(asyncio.sleep(3))
loop.run_until_complete(main_async(task_name="hello_sync", queue=QUEUE_NANE_01, body={"message": "hello sync task3"}))
loop.run_until_complete(main_async(task_name="hello_async", queue=QUEUE_NANE_02, body={"message": "hello async task4"}))

loop.run_until_complete(
    main_async(task_name="data_async", queue=QUEUE_NANE_01, body={"message": "async progress task"}))

loop.run_until_complete(client.close())

loop.close()
