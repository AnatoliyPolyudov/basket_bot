# telegram_observer.py
from observer import Observer
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
from datetime import datetime
import threading
import asyncio

class TelegramObserver(Observer):
    def __init__(self, token: str, chat_id: str, trader=None):
        self.chat_id = chat_id
        self.trader = trader

        # Создаём приложение для polling
        self.app = Application.builder().token(token).build()

        # Обработчики
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CallbackQueryHandler(self.button_handler))

        # Запуск polling в отдельном потоке
        threading.Thread(target=self.app.run_polling, daemon=True).start()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Бот запущен. Я буду присылать торговые сигналы.")

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        action = query.data

        # Вызываем методы трейдера
        if self.trader:
            if action == "Открыть позицию":
                self.trader.open_position("BTC/USDT")
            elif action == "Закрыть позицию":
                self.trader.close_position("BTC/USDT")

        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"[Paper] Вы выбрали: {action}")

    def update(self, data):
        """Вызывается синхронно из монитора"""
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

        # Используем run_coroutine_threadsafe, чтобы безопасно вызвать асинхронный метод из синхронного потока
        asyncio.run_coroutine_threadsafe(
            self.app.bot.send_message(
                chat_id=self.chat_id,
                text=msg,
                reply_markup=reply_markup
            ),
            self.app.loop
        )
