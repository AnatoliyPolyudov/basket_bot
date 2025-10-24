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
        pair_name = pair_data.get('pair_name', 'UNKNOWN')
        signal = pair_data.get('signal', 'NO_SIGNAL')
        z_score = pair_data.get('z_score', 0)
        adf_passed = pair_data.get('adf_passed', False)
        
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
            f"Z-score: {z_score:.2f if z_score else 'N/A'}\n"
            f"ADF: {'✅ PASSED' if adf_passed else '❌ FAILED'}"
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
    
    def send_status_report(self, report_data: Dict, open_positions: List = None) -> bool:
        """Отправка статус отчета"""
        if not report_data:
            return False
            
        open_positions = open_positions or []
        
        # Основная статистика
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
                message += f"• {pos.get('pair', 'N/A')} - {pos.get('signal', 'N/A')}\n"
        
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
                action, signal, pair_name = callback_data.split(':', 2)
                if action == 'OPEN':
                    success = positions_manager.open_position(signal, pair_name)
                    msg = f"✅ Opened position: {pair_name}" if success else f"❌ Failed to open: {pair_name}"
                else:
                    success = positions_manager.close_position(signal, pair_name)
                    msg = f"✅ Closed position: {pair_name}" if success else f"❌ Failed to close: {pair_name}"
                return self.send_message(msg)
                
            return True
            
        except Exception as e:
            logger.error(f"Error handling callback: {e}")
            return self.send_message(f"❌ Error: {str(e)}")


class SimplePositionsManager:
    """Упрощенный менеджер позиций (без реального трейдинга)"""
    def __init__(self):
        self.open_positions = []
        
    def open_position(self, signal: str, pair_name: str) -> bool:
        """Открытие позиции (демо)"""
        position = {
            'pair': pair_name,
            'signal': signal,
            'size': 1000,
            'entry_time': '2024-10-24'
        }
        self.open_positions.append(position)
        logger.info(f"Opened position: {pair_name} - {signal}")
        return True
        
    def close_position(self, signal: str, pair_name: str) -> bool:
        """Закрытие позиции (демо)"""
        self.open_positions = [p for p in self.open_positions if p['pair'] != pair_name]
        logger.info(f"Closed position: {pair_name}")
        return True
        
    def close_all_positions(self) -> int:
        """Закрытие всех позиций"""
        count = len(self.open_positions)
        self.open_positions.clear()
        logger.info(f"Closed all {count} positions")
        return count
        
    def get_open_positions(self) -> List:
        """Получение открытых позиций"""
        return self.open_positions.copy()
