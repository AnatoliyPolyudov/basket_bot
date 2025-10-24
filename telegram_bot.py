# telegram_bot.py - Упрощенный Telegram бот с кнопками
import requests
import json
import logging
from typing import Optional, List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
        
    def safe_format_number(self, value, precision=2):
        """Безопасное форматирование чисел"""
        try:
            if value is None:
                return "N/A"
            return f"{float(value):.{precision}f}"
        except (ValueError, TypeError):
            return str(value)
        
    def send_message(self, text: str, buttons: Optional[List] = None) -> bool:
        """Отправка сообщения с кнопками"""
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        
        if buttons:
            payload['reply_markup'] = json.dumps({'inline_keyboard': buttons})
            
        try:
            response = requests.post(f"{self.base_url}/sendMessage", json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    def send_signal_alert(self, pair_data: Dict) -> bool:
        """Отправка сигнала с кнопками действий"""
        try:
            pair_name = pair_data.get('pair_name', 'UNKNOWN')
            signal = pair_data.get('signal', 'NO_SIGNAL')
            z_score = pair_data.get('z_score')
            adf_passed = pair_data.get('adf_passed', False)
            price_a = pair_data.get('price_a')
            price_b = pair_data.get('price_b')
            
            # Безопасное форматирование
            z_display = self.safe_format_number(z_score, 2)
            price_a_display = self.safe_format_number(price_a, 2)
            price_b_display = self.safe_format_number(price_b, 2)
            
            # Форматируем сигнал
            formatted_signal = signal
            if "SHORT_" in signal and "LONG_" in signal:
                parts = signal.split('_')
                if len(parts) >= 4:
                    formatted_signal = f"SHORT {parts[1]} / LONG {parts[3]}"
            
            message = (
                f"🎯 <b>TRADING SIGNAL</b>\n"
                f"Pair: <b>{pair_name}</b>\n"
                f"Signal: <b>{formatted_signal}</b>\n"
                f"Z-score: {z_display}\n"
                f"ADF: {'✅ PASSED' if adf_passed else '❌ FAILED'}\n"
                f"Prices: {price_a_display} | {price_b_display}"
            )
            
            # Кнопки только для торговых сигналов
            buttons = None
            if signal not in ['HOLD', 'NO_DATA', 'EXIT_POSITION']:
                buttons = [
                    [
                        {'text': '📈 OPEN', 'callback_data': f'OPEN:{signal}:{pair_name}'},
                        {'text': '❌ CLOSE', 'callback_data': f'CLOSE:{signal}:{pair_name}'}
                    ]
                ]
            elif signal == 'EXIT_POSITION':
                buttons = [
                    [{'text': '🔴 CLOSE POSITION', 'callback_data': f'CLOSE:{signal}:{pair_name}'}]
                ]
                
            return self.send_message(message, buttons)
            
        except Exception as e:
            logger.error(f"Error in send_signal_alert: {e}")
            return self.send_message(f"❌ Error generating signal: {str(e)}")
    
    def send_status_report(self, report_data: Dict, open_positions: List = None) -> bool:
        """Отправка статус отчета"""
        try:
            if not report_data:
                return self.send_message("❌ No report data available")
                
            open_positions = open_positions or []
            
            # Безопасное извлечение данных
            total_pairs = report_data.get('total_pairs', 0)
            active_pairs = report_data.get('active_pairs', 0)
            trading_signals = report_data.get('trading_signals', 0)
            
            message = (
                f"📊 <b>PAIRS MONITORING STATUS</b>\n"
                f"Total Pairs: {total_pairs}\n"
                f"Active Pairs: {active_pairs}\n"
                f"Trading Signals: {trading_signals}\n"
                f"Open Positions: {len(open_positions)}"
            )
            
            # Детали по открытым позициям
            if open_positions:
                message += "\n\n🎯 <b>OPEN POSITIONS:</b>\n"
                for pos in open_positions[:5]:  # Ограничиваем для читаемости
                    pair_name = pos.get('pair', 'N/A')
                    signal = pos.get('signal', 'N/A')
                    message += f"• {pair_name} - {signal}\n"
            
            # Кнопки управления
            buttons = [
                [
                    {'text': '📈 Summary', 'callback_data': 'SUMMARY'},
                    {'text': '🛑 Close All', 'callback_data': 'CLOSE_ALL'}
                ],
                [
                    {'text': '🔄 Refresh', 'callback_data': 'REFRESH'}
                ]
            ]
            
            return self.send_message(message, buttons)
            
        except Exception as e:
            logger.error(f"Error in send_status_report: {e}")
            return self.send_message(f"❌ Error generating status report: {str(e)}")
    
    def handle_callback(self, callback_data: str, pair_analyzer, positions_manager) -> bool:
        """Обработка callback от кнопок"""
        try:
            if callback_data == 'SUMMARY':
                report = pair_analyzer.get_analysis_report()
                return self.send_status_report(report, positions_manager.get_open_positions())
                
            elif callback_data == 'CLOSE_ALL':
                closed_count = positions_manager.close_all_positions()
                return self.send_message(f"✅ Closed {closed_count} positions")
                
            elif callback_data == 'REFRESH':
                report = pair_analyzer.get_analysis_report()
                return self.send_status_report(report, positions_manager.get_open_positions())
                
            elif callback_data.startswith(('OPEN:', 'CLOSE:')):
                # Обработка торговых команд
                try:
                    action, signal, pair_name = callback_data.split(':', 2)
                    if action == 'OPEN':
                        success = positions_manager.open_position(signal, pair_name)
                        msg = f"✅ Opened position: {pair_name}" if success else f"❌ Failed to open: {pair_name}"
                    else:
                        success = positions_manager.close_position(signal, pair_name)
                        msg = f"✅ Closed position: {pair_name}" if success else f"❌ Failed to close: {pair_name}"
                    return self.send_message(msg)
                except ValueError:
                    return self.send_message("❌ Invalid callback format")
                
            return self.send_message(f"❌ Unknown command: {callback_data}")
            
        except Exception as e:
            logger.error(f"Error handling callback: {e}")
            return self.send_message(f"❌ Error: {str(e)}")


class SimplePositionsManager:
    """Упрощенный менеджер позиций (без реального трейдинга)"""
    def __init__(self):
        self.open_positions = []
        
    def open_position(self, signal: str, pair_name: str) -> bool:
        """Открытие позиции (демо)"""
        try:
            position = {
                'pair': pair_name,
                'signal': signal,
                'size': 1000,
                'entry_time': '2024-10-24'
            }
            self.open_positions.append(position)
            logger.info(f"Opened position: {pair_name} - {signal}")
            return True
        except Exception as e:
            logger.error(f"Error opening position: {e}")
            return False
        
    def close_position(self, signal: str, pair_name: str) -> bool:
        """Закрытие позиции (демо)"""
        try:
            initial_count = len(self.open_positions)
            self.open_positions = [p for p in self.open_positions if p['pair'] != pair_name]
            closed = initial_count - len(self.open_positions)
            logger.info(f"Closed position: {pair_name} ({closed} positions)")
            return closed > 0
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return False
        
    def close_all_positions(self) -> int:
        """Закрытие всех позиций"""
        try:
            count = len(self.open_positions)
            self.open_positions.clear()
            logger.info(f"Closed all {count} positions")
            return count
        except Exception as e:
            logger.error(f"Error closing all positions: {e}")
            return 0
        
    def get_open_positions(self) -> List:
        """Получение открытых позиций"""
        return self.open_positions.copy()
