import inspect
import json

from aio_pika import Message

from mqtasks.context import MqTaskContext
from mqtasks.headers import MqTaskHeaders
from mqtasks.response_types import MqTaskResponseTypes


class MqTaskRegister:
    def __init__(
            self,
            name: str,
            func
    ):
        self.name = name
        self.func = func

    async def invoke_async(self, ctx: MqTaskContext, verbose: bool):
        if verbose:
            ctx.logger.debug("______________________________________________")
            ctx.logger.debug(f"invoke begin task:{ctx.name} with_id:{ctx.id}")

        func_result = None
        if inspect.iscoroutinefunction(self.func):
            func_result = await self.func(ctx)
        else:
            func_result = self.func(ctx)

        data_result: bytes | None = None
        if func_result is not None:
            if isinstance(func_result, str):
                data_result = func_result.encode()
            elif isinstance(func_result, bytes):
                data_result = func_result
            else:
                data_result = json.dumps(func_result).encode()

        await ctx.exchange.publish(
            Message(
                headers={
                    MqTaskHeaders.TASK: ctx.name,
                    MqTaskHeaders.ID: ctx.id,
                    MqTaskHeaders.RESPONSE_TO_MESSAGE_ID: ctx.message_id,
                    MqTaskHeaders.RESPONSE_TYPE: MqTaskResponseTypes.RESPONSE
                },
                message_id=ctx.message_id_factory.new_id(),
                body=data_result or bytes()),
            routing_key=ctx.exchange.name,
        )

        if verbose:
            ctx.logger.debug(f"invoke end task:{ctx.name} with_id:{ctx.id} result:{func_result}")
            ctx.logger.debug("--------------------------------------------")
