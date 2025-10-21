import asyncio
from telegram import Bot

async def main():
    bot = Bot(token="8436652130:AAF6On0GJtRHfMZyqD3mpM57eXZfWofJeng")
    me = await bot.get_me()
    print(me)

asyncio.run(main())
