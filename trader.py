# telegram_observer.py (обновлённый фрагмент)

class TelegramObserver(Observer):
    def __init__(self, token: str, chat_id: str, trader=None):
        self.bot = Bot(token=token)
        self.chat_id = chat_id
        self.trader = trader  # подключаем трейдера

        self.app = Application.builder().token(token).build()
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CallbackQueryHandler(self.button_handler))

        thread = threading.Thread(target=self._run_polling, daemon=True)
        thread.start()

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        action = query.data

        # Вызываем методы трейдера
        if self.trader:
            if action == "Открыть позицию":
                self.trader.open_position("BTC/USDT")  # можно менять символ
            elif action == "Закрыть позицию":
                self.trader.close_position("BTC/USDT")

        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"[Paper] Вы выбрали: {action}")
