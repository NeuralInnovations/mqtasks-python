import asyncio
import logging
from mqtasks import run_mqtasks

from example.example_config import CONNECTION, QUEUE_NANE_REQUEST_01, QUEUE_NANE_REQUEST_02, QUEUE_NANE_PUBLISH_01
from mqtasks import MqTasks, MqTaskContext

logging.basicConfig(level=logging.DEBUG)
# CREATE NEW MESSAGE QUEUE TASK HANDLER
tasks = MqTasks(
    amqp_connection=CONNECTION,
    queue_name=QUEUE_NANE_REQUEST_01,
    logger=logging.getLogger(QUEUE_NANE_REQUEST_01),
    logging_level=logging.DEBUG
)

lists = MqTasks(
    amqp_connection=CONNECTION,
    queue_name=QUEUE_NANE_REQUEST_02,
    logger=logging.getLogger(QUEUE_NANE_REQUEST_02),
    logging_level=logging.DEBUG,
)

publish = MqTasks(
    amqp_connection=CONNECTION,
    queue_name=QUEUE_NANE_PUBLISH_01,
    logger=logging.getLogger(QUEUE_NANE_PUBLISH_01),
    logging_level=logging.DEBUG,
)


# DECLARE THE SYNC REQUEST TASK
@tasks.task(name="hello_sync")
def hello_sync(ctx: MqTaskContext):
    print(f"{'request' if ctx.is_request else 'task'} mid:{ctx.message_id} name:{ctx.name} id:{ctx.id} reply_to:{ctx.reply_to} body:{ctx.body.as_json()}")

    # test exception
    raise Exception("hello_sync")

    return {
        "message": "Hello world too!!! :)"
    }


# DECLARE THE ASYNC REQUEST TASK
@lists.task(name="hello_async")
async def hello_async(ctx: MqTaskContext):
    print(f"{'request' if ctx.is_request else 'task'} mid:{ctx.message_id} name:{ctx.name} id:{ctx.id} reply_to:{ctx.reply_to} body:{ctx.body.as_json()}")
    # sleep
    await asyncio.sleep(1)
    return {
        "message": "Hello world too!!! :)"
    }


# DECLARE THE ASYNC REQUEST TASK
@tasks.task(name="data_async")
async def data_async(ctx: MqTaskContext):
    print(f"{'request' if ctx.is_request else 'task'} mid:{ctx.message_id} name:{ctx.name} id:{ctx.id} reply_to:{ctx.reply_to} body:{ctx.body.as_json()}")
    # sleep
    await asyncio.sleep(1)
    await ctx.publish_data_async(body={"progress": 0.2})
    # await asyncio.sleep(5)
    await ctx.publish_data_async(body={"progress": 0.5})
    # await asyncio.sleep(5)
    await ctx.publish_data_async(body={"progress": 0.7})
    return {
        "progress": 1
    }

# DECLARE THE ASYNC TASK
@publish.task(name="task_async", log_body=False)
async def task_async(ctx: MqTaskContext):
    await asyncio.sleep(0)
    print(f"{'request' if ctx.is_request else 'task'} mid:{ctx.message_id} name:{ctx.name} id:{ctx.id} reply_to:{ctx.reply_to} body:{ctx.body.as_json()}")
    return {}

# NEED TO RUN
run_mqtasks(tasks=[
    tasks, lists, publish
])
