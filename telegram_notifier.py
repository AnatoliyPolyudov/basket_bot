import logging
import requests
from typing import Optional
from config import config

class TelegramNotifier:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.bot_token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.enabled = config.TELEGRAM_ENABLED and self.bot_token and self.chat_id
        
        if self.enabled:
            self.logger.info("Telegram notifier initialized")
        else:
            self.logger.warning("Telegram notifier disabled - check token and chat_id")
    
    def send_message(self, message: str) -> bool:
        if not self.enabled:
            return False
            
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            self.logger.error(f"Error sending Telegram message: {e}")
            return False
    
    def signal_alert(self, signal_type: str, z_score: float, ratio: float) -> bool:
        message = (
            f"TRADING SIGNAL\n"
            f"Type: {signal_type}\n"
            f"Z-Score: {z_score:.2f}\n"
            f"Ratio: {ratio:.6f}\n"
            f"Pair: {config.TARGET_PAIR}"
        )
        return self.send_message(message)
    
    def position_closed(self, pnl: float, duration: str) -> bool:
        message = (
            f"POSITION CLOSED\n"
            f"PnL: {pnl:.2f}bps\n"
            f"Duration: {duration}\n"
            f"Pair: {config.TARGET_PAIR}"
        )
        return self.send_message(message)
    
    def error_alert(self, error_msg: str) -> bool:
        message = (
            f"SYSTEM ERROR\n"
            f"Error: {error_msg}\n"
            f"Pair: {config.TARGET_PAIR}"
        )
        return self.send_message(message)
    
    def system_start(self) -> bool:
        message = (
            f"SYSTEM STARTED\n"
            f"Target: {config.TARGET_PAIR}\n"
            f"Basket Size: {config.BASKET_SIZE}\n"
            f"Z-Enter: {config.Z_ENTER}\n"
            f"Z-Exit: {config.Z_EXIT}"
        )
        return self.send_message(message)

# Global notifier instance
telegram = TelegramNotifier()
