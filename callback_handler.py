# callback_handler.py
def handle_callback(callback_data, trader, telegram_observer=None):
    """
    Обработка нажатий кнопок Telegram.
    """
    try:
        # 🆕 ОБРАБАТЫВАЕМ КОМАНДЫ УПРАВЛЕНИЯ
        if callback_data in ['SUMMARY', 'CLOSE_ALL', 'ENABLE_AUTO', 'DISABLE_AUTO']:
            if telegram_observer:
                telegram_observer.handle_management_callback(callback_data, trader)
            return
            
        # Обработка торговых команд
        parts = callback_data.split(":", 2)
        if len(parts) == 3:
            action, signal, pair_name = parts
        elif len(parts) == 2:
            action, signal = parts
            pair_name = "UNKNOWN"
        else:
            print(f"❌ Invalid callback format: {callback_data}")
            return
            
        if trader is None:
            print("❌ Trader not provided for callback")
            return

        if action == "OPEN":
            # 🆕 ДОБАВЛЯЕМ МЕТКУ MANUAL ДЛЯ ОТСЛЕЖИВАНИЯ
            trader.open_position(f"MANUAL_{signal}", pair_name)
        elif action == "CLOSE":
            trader.close_position(signal, pair_name, "Manual close from Telegram")
        else:
            print(f"❌ Unknown callback action: {action}")
    except Exception as e:
        print(f"❌ Callback handler error: {e}")