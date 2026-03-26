# Telemicro

Telemicro is easy to use and asynchronous module for working with [Telegram Bot API](https://core.telegram.org/bots/api), written on Micropython.

----

## Example

Simple example of using Telemicro features

```python
import network
import uasyncio
from telemicro.bot import Bot
from telemicro.dispatcher import Dispatcher, Router
from telemicro.requests import Requests

# Connecting to WiFi
nic = network.WLAN(network.STA_IF)
nic.active(True)
nic.connect("SomeNetwork", "SuperSecurePass123")

router = Router()

# Creating some basic filter
class TextFilter:
    def __init__(self, text):
        self.text = text

    def __call__(self, message, data):
        if message["text"] == self.text:
            return True
        return False

async def handler(message, kwargs):
    bot_ = kwargs.get("bot")
    text = kwargs.get("text")
    data = {"chat_id": message["from"]["id"], "text": text}
    # sending answer to user, using api request
    await bot_.api_request("sendMessage", data)

# Register handler to router using decorator
@router.message(TextFilter("/about"))
async def decorator_handler(message, kwargs):
    bot = kwargs["bot"]
    text = "Hi! I'm bot made with telemicro, on Micropython"
    data = {"chat_id": message["from"]["id"], "text": text}
    # sending answer to user, using api request
    await bot.api_request("sendMessage", data)

    
if __name__ == "__main__":
    dp = Dispatcher()
    bot = Bot("123456789:ABCDEFGHIJK")

    # Registering handler to router using function
    router.message.register(handler, TextFilter("/start"))
    dp.include_router(router)

    # passing params via dispatcher
    uasyncio.run(dp.start_polling(bot, text="Heeeyya from telemicro!"))
```

## Licences

Telemicro module contains code from other repositories and users, which are included 
in the file code ([dispatcher.py](./telemicro/dispatcher.py) - event observer names 
& some logic from aiogram, [requests.py](./telemicro/requests.py) - requests module by 
popnotsoda95, [ulogging.py](./telemicro/ulogging.py) - by Youkii-Chen). 

**These files are required for Telemicro to work properly - so when using Telemicro you 
are automatically acknowledging these licences**

## Contributing

We'd love for you to create pull requests from the development branch (develop). 
Latest releases are created from the main branch.

## Contact us

- Alex ([GitHub](https://github.com/aliakseych))