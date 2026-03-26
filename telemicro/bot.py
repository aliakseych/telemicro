try:
    import json
except ImportError:
    import ujson as json

try:
    import asyncio
except ImportError:
    import uasyncio as asyncio
from .requests import Requests


class GetUpdatesError(Exception):
    pass


class Base:
    def __init__(self, token: str,
                 server: str = "https://api.telegram.org"):
        # Do not change logger's value
        self._logger = None
        self.token = token
        self.server = server
        self.requests = Requests()
        self.offset = 0
        self.updates = []

    async def api_request(self, method: str,
                          data: dict):
        url = f"{self.server}/bot{self.token}/{method}"
        self._logger.info(f"API request - {method}; {str(data)} has requested")
        response = await self.requests.get(url=url, params=data)
        return json.loads(response.data)

    async def getUpdates(self, allowed_updates: list[str],
                         offset: int):
        url = f"{self.server}/bot{self.token}/getUpdates"
        params = {
            "allowed_updates": allowed_updates,
            "offset": offset
        }
        response = await self.requests.get(url=url,
                                           params=params)
        data = json.loads(response.data)
        if not data["ok"]:
            error = f"{data['error_code']}: {data['description']}"
            self._logger.error(f"getUpdates was unsuccessful with error {error}")
            raise GetUpdatesError(error)
        self._logger.info(f"getUpdates was success")
        return data.get("result")

    def set_logger(self, logger):
        """Setting default logger for bot after starting polling"""
        self._logger = logger


class Bot(Base):
    def getMe(self):
        self.api_request("getMe", {})

    def close(self):
        self.api_request("close", {})


class UpdatesGetter:
    def __init__(self, bot: Bot,
                 allowed_updates: list[str]):
        self.bot = bot
        self.allowed_updates = allowed_updates
        self.offset = 0

    def __aiter__(self):
        self.updates = []
        self.updates_amount = 0
        self.current_update = 0
        self.updates_executed = 0
        self.update = None
        try:
            getUpdates = self.bot.getUpdates(self.allowed_updates, self.offset)
            self.updates = asyncio.run(getUpdates)
            self.updates_amount = len(self.updates)
        except TypeError:
            self.updates_amount = 0
        except Exception as exception:
            raise exception
        return self

    async def __anext__(self):
        if self.updates_amount == self.updates_executed:
            self.__aiter__()
            return None
        else:
            self.update = self.updates[self.current_update]
            self.offset = self.update["update_id"] + 1
            self.current_update += 1
            self.updates_executed += 1
            return self.update
