import asyncio

from example.example_config import CONNECTION, QUEUE_NANE
from mqtasks import MqTasksClient

loop = asyncio.get_event_loop()
client = MqTasksClient(
    loop=loop,
    amqp_connection=CONNECTION,
    verbose=True
)


async def main_async(task_name: str, body: str | object | None = None) -> None:
    channel = await client.queue(QUEUE_NANE)
    response = await channel.run_task_async(
        task_name=task_name,
        body=body,
        message_handler=lambda msg: print(msg)
    )
    print(response)


# ==============================================================================


loop.run_until_complete(main_async(task_name="hello_sync", body={"message": "hello sync task1"}))
loop.run_until_complete(main_async(task_name="hello_async", body={"message": "hello async task2"}))
loop.run_until_complete(main_async(task_name="hello_sync", body={"message": "hello sync task3"}))
loop.run_until_complete(main_async(task_name="hello_async", body={"message": "hello async task4"}))

loop.run_until_complete(main_async(task_name="data_async", body={"message": "async progress task"}))


loop.run_until_complete(client.close())

loop.close()
