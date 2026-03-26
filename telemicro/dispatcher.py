"""
Part of this code is under MIT License copyright

Copyright (c) 2017-2026 Alex Root Junior

Permission is hereby granted, free of charge, to any person obtaining a copy of this
software and associated documentation files (the "Software"), to deal in the Software
without restriction, including without limitation the rights to use, copy, modify,
merge, publish, distribute, sublicense, and/or sell copies of the Software,
and to permit persons to whom the Software is furnished to do so, subject to the
following conditions:

The above copyright notice and this permission notice shall be included in all copies
or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
OR OTHER DEALINGS IN THE SOFTWARE.
"""

try:
    import asyncio
except ImportError:
    import uasyncio as asyncio

from .ulogging import Logger
from .bot import Bot, UpdatesGetter


class Observer:
    def __init__(self, event_name: str):
        self.event_name = event_name
        self.handlers = []

    def register(self, func, *filters):
        handler = {"func": func, "filters": filters}
        self.handlers.append(handler)

    def __call__(self, *filters):
        """Register handlers via decorator"""
        def wrapper(func):
            self.register(func, filters)
            return func
        return wrapper


class Router:
    def __init__(self):
        self._logger = Logger(name="Router")
        self.children_routers = []

        self.message = Observer(event_name="message")
        self.edited_message = Observer(event_name="edited_message")
        self.channel_post = Observer(event_name="channel_post")
        self.edited_channel_post = Observer(event_name="edited_channel_post")
        self.inline_query = Observer(event_name="inline_query")
        self.chosen_inline_result = Observer(event_name="chosen_inline_result")
        self.callback_query = Observer(event_name="callback_query")
        self.shipping_query = Observer(event_name="shipping_query")
        self.pre_checkout_query = Observer(event_name="pre_checkout_query")
        self.poll = Observer(event_name="poll")
        self.poll_answer = Observer(event_name="poll_answer")
        self.my_chat_member = Observer(event_name="my_chat_member")
        self.chat_member = Observer(event_name="chat_member")
        self.chat_join_request = Observer(event_name="chat_join_request")
        self.error = Observer(event_name="error")

        self.observers = {
            "message": self.message,
            "edited_message": self.edited_message,
            "channel_post": self.channel_post,
            "edited_channel_post": self.edited_channel_post,
            "inline_query": self.inline_query,
            "chosen_inline_result": self.chosen_inline_result,
            "callback_query": self.callback_query,
            "shipping_query": self.shipping_query,
            "pre_checkout_query": self.pre_checkout_query,
            "poll": self.poll,
            "poll_answer": self.poll_answer,
            "my_chat_member": self.my_chat_member,
            "chat_member": self.chat_member,
            "chat_join_request": self.chat_join_request,
            "error": self.error,
        }

        self.allowed_updates = [
            "message",
            "edited_message",
            "channel_post",
            "edited_channel_post",
            "inline_query",
            "chosen_inline_result",
            "callback_query",
            "shipping_query",
            "pre_checkout_query",
            "poll",
            "poll_answer",
            "my_chat_member",
            "chat_member",
            "chat_join_request",
            "error",
        ]

    async def handle_update(self, update: dict,
                            event_loop,
                            kwargs):
        event_name = None
        for dateon in update:
            if dateon in self.observers:
                event_name = dateon
                break

        update_handler = self.get_handler(self, update, event_name, kwargs)

        if update_handler is None:
            for child_router in self.children_routers:
                update_handler = self.get_handler(child_router, update,
                                                  event_name, kwargs)

        if update_handler is not None:
            try:
                event_loop.run_until_complete(
                    update_handler(
                        update[event_name],
                        kwargs
                    ))
                self._logger.info(f"Update {update['update_id']} is handled")
                return
            except Exception as exception:
                self._logger.error(f"While handling update {update['update_id']}, got an error - {exception}")

        self._logger.info(f"Update {update['update_id']} is unhandled")

    def get_handler(self, router, update, event_name, kwargs):
        """Get handler from observers for handling update"""
        observer = router.observers.get(event_name)
        kwargs.update(router=router)
        update_handler = None
        for handler in observer.handlers:
            for filter_ in handler["filters"]:
                try:
                    self._logger.debug(f"Executing filter result is {filter_(update[event_name], kwargs)}")
                    result = await filter_(update[event_name], kwargs)
                    if result:
                        update_handler = handler["func"]
                        continue
                    update_handler = None
                    break
                except Exception as exception:
                    self._logger.error(f"Checking filter of handler was unsuccessful because {exception}")
                    break

        return update_handler

    def set_logger(self, logger: Logger):
        self._logger = logger


class Dispatcher(Router):
    def __init__(self):
        super().__init__()
        self.event_loop = asyncio.get_event_loop()
        self.event_loop.run_forever()
        self.bot = None
        self.polling = None

    async def start_polling(self, bot: Bot,
                            **kwargs):
        kwargs.update(bot=bot, dp=self)
        self.bot = bot
        bot.set_logger(self._logger)
        self.polling = True
        self._logger.info("Polling started")
        while self.polling:
            try:
                async for update in UpdatesGetter(bot, self.allowed_updates):
                    if update is not None:
                        self._logger.info(f"Handling update {update['update_id']}")
                        await self.handle_update(update, self.event_loop, kwargs)
            except Exception as exception:
                self._logger.error(f"While polling, got an error - {exception}")

    async def stop_polling(self):
        self.polling = False
        self._logger.info("Polling stopped")

    def include_router(self,
                       router: Router):
        self.children_routers.append(router)
