from telegram import Bot
import asyncio

async def main():
    bot = Bot(token="8436652130:AAF6On0GJtRHfMZyqD3mpM57eXZfWofJeng")
    await bot.send_message(chat_id="317217451", text="✅ Test message from script")

asyncio.run(main())
