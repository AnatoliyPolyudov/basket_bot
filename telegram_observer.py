from observer import Observer
from telegram import Bot
import asyncio
import threading
from datetime import datetime

class TelegramObserver(Observer):
    def __init__(self, token: str, chat_id: str):
        self.bot = Bot(token=token)
        self.chat_id = chat_id
        self.queue = asyncio.Queue()

        # Запускаем отдельный поток с собственным event loop
        self.loop = asyncio.new_event_loop()
        t = threading.Thread(target=self._start_loop, daemon=True)
        t.start()

    def _start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.create_task(self._worker())
        self.loop.run_forever()

    async def _worker(self):
        while True:
            msg = await self.queue.get()
            try:
                await self.bot.send_message(chat_id=self.chat_id, text=msg)
            except Exception as e:
                print(f"Failed to send Telegram message: {e}")
            self.queue.task_done()

    def update(self, data):
        msg = (
            f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}] Basket Monitor Update\n"
            f"Signal: {data['signal']}\n"
            f"Z-score: {data['z']:.4f}\n"
            f"Spread: {data['spread']:.6f}\n"
            f"Basket Price: {data['basket_price']:.2f}\n"
            f"Target Price: {data['target_price']:.2f}"
        )
        # Добавляем сообщение в очередь Telegram
        self.loop.call_soon_threadsafe(self.queue.put_nowait, msg)
