import asyncio

from example.example_config import CONNECTION, QUEUE_NANE
from mqtasks import MqTasks, MqTaskContext

# CREATE NEW MESSAGE QUEUE TASK HANDLER
tasks = MqTasks(amqp_connection=CONNECTION, queue_name=QUEUE_NANE)


# DECLARE THE SYNC TASK
@tasks.task(name="hello_sync")
def hello_sync(ctx: MqTaskContext):
    print(f"mid:{ctx.message_id} name:{ctx.name} id:{ctx.id} relay_to:{ctx.relay_to} body:{ctx.body.as_json()}")
    return {
        "message": "Hello world too!!! :)"
    }


# DECLARE THE ASYNC TASK
@tasks.task(name="hello_async")
async def hello_async(ctx: MqTaskContext):
    print(f"mid:{ctx.message_id} name:{ctx.name} id:{ctx.id} relay_to:{ctx.relay_to} body:{ctx.body.as_json()}")
    # sleep
    await asyncio.sleep(1)
    return {
        "message": "Hello world too!!! :)"
    }


# DECLARE THE ASYNC TASK
@tasks.task(name="data_async")
async def data_async(ctx: MqTaskContext):
    print(f"mid:{ctx.message_id} name:{ctx.name} id:{ctx.id} relay_to:{ctx.relay_to} body:{ctx.body.as_json()}")
    # sleep
    await asyncio.sleep(1)
    await ctx.publish_data_async(body={"progress": 0.2})
    await ctx.publish_data_async(body={"progress": 0.5})
    await ctx.publish_data_async(body={"progress": 0.7})
    return {
        "progress": 1
    }


# NEED TO RUN
tasks.run()
