import inspect
import json
import logging

from aio_pika import Message

from mqtasks.context import MqTaskContext
from mqtasks.headers import MqTaskHeaders
from mqtasks.response_types import MqTaskResponseTypes
from mqtasks.utils import to_json_bytes


class MqTaskRegister:
    def __init__(
            self,
            name: str,
            func
    ):
        self.name = name
        self.func = func

    async def invoke_async(self, ctx: MqTaskContext):
        if ctx.logger.isEnabledFor(logging.DEBUG):
            ctx.logger.debug("______________________________________________")
            ctx.logger.debug(f"invoke begin task:{ctx.name} with_id:{ctx.id}")

        func_result = None
        if inspect.iscoroutinefunction(self.func):
            func_result = await self.func(ctx)
        else:
            func_result = self.func(ctx)

        data_result: bytes | None = to_json_bytes(func_result)

        if ctx.exchange is not None:
            await ctx.exchange.publish(
                Message(
                    headers={
                        MqTaskHeaders.TASK: ctx.name,
                        MqTaskHeaders.RESPONSE_TO_MESSAGE_ID: ctx.message_id,
                        MqTaskHeaders.RESPONSE_TYPE: MqTaskResponseTypes.RESPONSE
                    },
                    correlation_id=ctx.id,
                    message_id=ctx.message_id_factory.new_id(),
                    body=data_result or bytes()),
                routing_key=ctx.exchange.name,
            )

        if ctx.logger.isEnabledFor(logging.DEBUG):
            ctx.logger.debug(f"invoke end task:{ctx.name} with_id:{ctx.id} result:{func_result}")
            ctx.logger.debug("--------------------------------------------")
