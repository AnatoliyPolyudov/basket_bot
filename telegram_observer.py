# telegram_observer.py

from observer import Observer
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime
import threading
import asyncio

class TelegramObserver(Observer):
    def __init__(self, token: str, chat_id: str):
        self.bot = Bot(token=token)
        self.chat_id = chat_id

        # Создаём приложение для polling
        self.app = Application.builder().token(token).build()

        # Регистрируем обработчики команд и кнопок
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CallbackQueryHandler(self.button_handler))

        # Запускаем polling в отдельном потоке
        thread = threading.Thread(target=self._run_polling, daemon=True)
        thread.start()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        await update.message.reply_text("Бот запущен. Я буду присылать торговые сигналы.")

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатываем нажатия кнопок"""
        query = update.callback_query
        await query.answer()

        action = query.data
        text = f"[Paper] Вы выбрали: {action}"
        print(text)  # логируем в консоль

        # Убираем кнопки после нажатия
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(text)

    def _run_polling(self):
        """Запускает polling в фоне"""
        asyncio.run(self.app.run_polling())

    def update(self, data):
        """Получает сигнал от монитора и отправляет сообщение с кнопками"""
        msg = (
            f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}] Basket Monitor Update\n"
            f"Signal: {data['signal']}\n"
            f"Z-score: {data['z']:.4f}\n"
            f"Spread: {data['spread']:.6f}\n"
            f"Basket Price: {data['basket_price']:.2f}\n"
            f"Target Price: {data['target_price']:.2f}"
        )

        keyboard = [
            [
                InlineKeyboardButton("Открыть позицию", callback_data="Открыть позицию"),
                InlineKeyboardButton("Закрыть позицию", callback_data="Закрыть позицию")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Используем loop бота, чтобы ставить задачу отправки сообщения
        loop = self.app.bot.loop
        if loop.is_running():
            loop.create_task(
                self.bot.send_message(
                    chat_id=self.chat_id,
                    text=msg,
                    reply_markup=reply_markup
                )
            )
        else:
            print(f"❌ Event loop не запущен, не удалось отправить сообщение: {data['signal']}")
