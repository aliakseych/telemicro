import network

try:
    import asyncio
except ImportError:
    import uasyncio as asyncio
from telemicro.bot import Bot
from telemicro.dispatcher import Dispatcher, Router

nic = network.WLAN(network.STA_IF)
nic.active(True)
nic.connect("SomeNetwork", "SuperSecurePass123")

# routers should divide handlers considering to the logic of the code
dp = Dispatcher()
router = Router()


# filter example
class TextFilter:
    def __init__(self, text):
        self.text = text

    async def __call__(self, message, data):
        if message["text"] == self.text:
            return True
        return False


# register handler using decorator
@router.message(TextFilter("/about"))
async def handler(message, kwargs):
    bot = kwargs["bot"]
    text = "Hi! I'm bot made with telemicro, on Micropython"
    data = {"chat_id": message["from"]["id"], "text": text}
    # sending answer to user, using api request
    await bot.api_request("sendMessage", data)


async def handler2(message, kwargs):
    bot = kwargs["bot"]
    text = kwargs["text"]
    data = {"chat_id": message["from"]["id"], "text": text}
    # sending answer to user, using api request
    await bot.api_request("sendMessage", data)


async def main():
    token = input("Your Bot Api token: ")
    bot = Bot(token=token)

    # register handler using func
    router.message.register(handler2, TextFilter("/start"))
    # including router, to handle updates using handlers from it
    dp.include_router(router)

    text = input("Some text for start: ")
    # passing additional arguments, to use them in handlers
    await dp.start_polling(bot, text=text)

if __name__ == "__main__":
    asyncio.run(main())