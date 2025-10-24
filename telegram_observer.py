from observer import Observer
import json
import requests
from callback_handler import handle_callback

TELEGRAM_BOT_TOKEN = "8436652130:AAF6On0GJtRHfMZyqD3mpM57eXZfWofJeng"
TELEGRAM_CHAT_ID = 317217451

class TelegramObserver(Observer):
    def __init__(self, trader=None):
        self.token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.trader = trader
        self.last_signals = {}
        self.last_zs = {}
        self.last_status_message = None  # 🆕 Для избежания спама

    def send_message(self, text, buttons=None):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        if buttons:
            payload['reply_markup'] = json.dumps({'inline_keyboard': buttons})
        try:
            requests.post(url, data=payload, timeout=10)
            print("Telegram message sent")
        except Exception as e:
            print("Telegram send failed:", e)

    def update(self, data):
        pairs_data = data.get('pairs_data', [])
        
        # 🆕 ОТПРАВЛЯЕМ СТАТУС ПОЗИЦИЙ КАЖДЫЕ 10 МИНУТ
        current_time = datetime.now()
        if (not self.last_status_message or 
            (current_time - self.last_status_message).total_seconds() > 600):  # 10 минут
        
            status_msg = self.generate_positions_status()
            if status_msg:
                self.send_message(status_msg)
                self.last_status_message = current_time
        
        # ... остальной код обработки сигналов ...

    # 🆕 МЕТОД ДЛЯ СТАТУСА ПОЗИЦИЙ
    def generate_positions_status(self):
        """Генерирует статус открытых позиций"""
        if not self.trader:
            return None
            
        open_positions = self.trader.get_open_positions()
        if not open_positions:
            return None
            
        msg = "📊 <b>OPEN POSITIONS STATUS</b>\n\n"
        
        for pair_name, position in open_positions.items():
            duration = (datetime.now() - position['entry_time']).total_seconds() / 60
            msg += (
                f"🎯 <b>{pair_name}</b>\n"
                f"Signal: {position['signal']}\n"
                f"Size: {position['size']}\n"
                f"Entry Z: {position['entry_z']:.2f}\n"
                f"Duration: {duration:.1f} min\n"
                f"Type: {position['type']}\n"
                f"-------------------\n"
            )
        
        # 🆕 КНОПКИ ДЛЯ УПРАВЛЕНИЯ
        buttons = [
            [
                {'text': '📊 Trading Summary', 'callback_data': 'SUMMARY'},
                {'text': '🛑 Close All', 'callback_data': 'CLOSE_ALL'}
            ],
            [
                {'text': '✅ Enable Auto', 'callback_data': 'ENABLE_AUTO'},
                {'text': '🚫 Disable Auto', 'callback_data': 'DISABLE_AUTO'}
            ]
        ]
        
        self.send_message(msg, buttons)
        return msg

    # 🆕 ОБРАБОТКА НОВЫХ CALLBACK ДЛЯ УПРАВЛЕНИЯ
    def handle_management_callback(self, callback_data, trader):
        """Обработка callback для управления торговлей"""
        if callback_data == 'SUMMARY':
            summary = trader.get_trading_summary()
            msg = (
                f"📈 <b>TRADING SUMMARY</b>\n"
                f"Total Trades: {summary['total_trades']}\n"
                f"Open Positions: {summary['open_positions']}\n"
                f"Current: {', '.join(summary['current_positions']) if summary['current_positions'] else 'None'}\n"
            )
            self.send_message(msg)
            
        elif callback_data == 'CLOSE_ALL':
            closed_count = trader.close_all_positions()
            self.send_message(f"✅ Closed {closed_count} positions")
            
        elif callback_data == 'ENABLE_AUTO':
            trader.enable_trading()
            self.send_message("✅ Auto trading ENABLED")
            
        elif callback_data == 'DISABLE_AUTO':
            trader.disable_trading()
            self.send_message("🚫 Auto trading DISABLED")