# callback_handler.py
def handle_callback(callback_data, trader):
    """
    Обработка нажатий кнопок Telegram.
    callback_data: 'OPEN:LONG BTC / SHORT BASKET' или 'CLOSE:LONG BTC / SHORT BASKET'
    """
    try:
        action, signal = callback_data.split(":", 1)
        if trader is None:
            print("❌ Trader not provided for callback")
            return

        if action == "OPEN":
            trader.open_position(signal)
        elif action == "CLOSE":
            trader.close_position(signal)
        else:
            print(f"❌ Unknown callback action: {action}")
    except Exception as e:
        print(f"❌ Callback handler error: {e}")
