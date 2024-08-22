import inspect
import logging
from typing import Any, Dict

from aio_pika import Message
from pamqp.common import FieldValue

from mqtasks.context import MqTaskContext
from mqtasks.headers import MqTaskHeaders
from mqtasks.response_status import MqResponseStatus
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

        has_exception: bool = False
        exception_msq: str | None = None
        func_result: Any | None = None
        try:
            if inspect.iscoroutinefunction(self.func):
                func_result = await self.func(ctx)
            else:
                func_result = self.func(ctx)
        except Exception as e:
            has_exception = True
            exception_msq = str(e)
            ctx.logger.exception(e)
        except Any as e:
            has_exception = True
            exception_msq = str(e)
            ctx.logger.error(e)

        if has_exception:
            func_result = exception_msq

        if not ctx.is_request and func_result is not None:
            ctx.logger.error(f"task:{ctx.name} with_id:{ctx.id} return value bust be None, current:{str(func_result)}")

        if ctx.is_request:
            data_result: bytes | None = to_json_bytes(func_result)

            if ctx.exchange is not None:
                headers: Dict[str, FieldValue] = {
                    MqTaskHeaders.TASK: ctx.name,
                    MqTaskHeaders.RESPONSE_TO_MESSAGE_ID: ctx.message_id,
                    MqTaskHeaders.RESPONSE_TYPE: MqTaskResponseTypes.RESPONSE,
                    MqTaskHeaders.RESPONSE_STATUS: MqResponseStatus.FAILURE if has_exception else MqResponseStatus.SUCCESS
                }
                if has_exception:
                    headers[MqTaskHeaders.RESPONSE_ERROR_MESSAGE] = exception_msq

                await ctx.exchange.publish(
                    Message(
                        headers=headers,
                        correlation_id=ctx.id,
                        message_id=ctx.message_id_factory.new_id(),
                        body=data_result or bytes()
                    ),
                    routing_key=ctx.routing_key,
                )

        if ctx.logger.isEnabledFor(logging.DEBUG):
            ctx.logger.debug(f"invoke end task:{ctx.name} with_id:{ctx.id} result:{func_result}")
            ctx.logger.debug("--------------------------------------------")
