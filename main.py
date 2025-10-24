# main.py - Главный файл для запуска
import time
import logging
import os
from pairs_core import PairAnalyzer
from telegram_bot import TelegramBot, SimplePositionsManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    # Инициализация компонентов
    analyzer = PairAnalyzer()
    positions_manager = SimplePositionsManager()
    
    # Telegram бот (токен из .env)
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN', '8436652130:AAF6On0GJtRHfMZyqD3mpM57eXZfWofJeng')
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '317217451')
    
    bot = TelegramBot(telegram_token, chat_id)
    
    logger.info("🚀 Starting Simplified Pairs Monitor...")
    bot.send_message("🤖 Pairs Monitor Started!")
    
    # Основной цикл мониторинга
    while True:
        try:
            # Получаем анализ пар
            report = analyzer.get_analysis_report()
            
            if 'error' not in report:
                # Отправляем статус каждые 10 минут
                bot.send_status_report(report, positions_manager.get_open_positions())
                
                # Проверяем и отправляем сигналы
                for pair_data in report['pairs_data']:
                    signal = pair_data.get('signal')
                    if signal not in ['HOLD', 'NO_DATA']:
                        bot.send_signal_alert(pair_data)
            
            # Ждем перед следующим обновлением
            time.sleep(600)  # 10 минут
            
        except KeyboardInterrupt:
            logger.info("🛑 Monitor stopped by user")
            bot.send_message("🛑 Pairs Monitor Stopped")
            break
        except Exception as e:
            logger.error(f"❌ Error in main loop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
