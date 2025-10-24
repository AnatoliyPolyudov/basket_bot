# callback_handler.py
def handle_callback(callback_data, trader):
    """
    Обработка нажатий кнопок Telegram.
    callback_data: 'OPEN:SHORT_BTC_LONG_ETH:BTC_ETH' или 'CLOSE:SHORT_BTC_LONG_ETH:BTC_ETH'
    """
    try:
        # 🆕 Обрабатываем новый формат с именем пары
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
            trader.open_position(signal, pair_name)
        elif action == "CLOSE":
            trader.close_position(signal, pair_name)
        else:
            print(f"❌ Unknown callback action: {action}")
    except Exception as e:
        print(f"❌ Callback handler error: {e}")