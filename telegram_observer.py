from observer import Observer
import json
import requests
from callback_handler import handle_callback
from datetime import datetime

TELEGRAM_BOT_TOKEN = "8436652130:AAF6On0GJtRHfMZyqD3mpM57eXZfWofJeng"
TELEGRAM_CHAT_ID = 317217451

class TelegramObserver(Observer):
    def __init__(self, trader=None):
        self.token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.trader = trader
        self.last_signals = {}
        self.last_zs = {}
        self.last_status_message = None

    def send_message(self, text, buttons=None):
        """Отправка сообщения в Telegram"""
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        if buttons:
            payload['reply_markup'] = json.dumps({'inline_keyboard': buttons})
        try:
            response = requests.post(url, data=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Telegram send failed: {e}")
            return False

    def safe_format_number(self, value, default=0, precision=2):
        """Безопасное форматирование чисел"""
        try:
            if value is None:
                return default
            return round(float(value), precision)
        except (ValueError, TypeError):
            return default

    def update(self, data):
        """Обновление данных от монитора"""
        pairs_data = data.get('pairs_data', [])
        current_time = datetime.now()
        
        # 🆕 УЛУЧШЕННАЯ ЛОГИКА ОТПРАВКИ СТАТУСА
        should_send_status = False
        
        if not self.last_status_message:
            should_send_status = True
        else:
            time_since_last = (current_time - self.last_status_message).total_seconds()
            if time_since_last > 600:  # 10 минут
                should_send_status = True
        
        if should_send_status:
            success = self.send_detailed_status(self.trader, data)
            if success:
                self.last_status_message = current_time
        
        # Обработка торговых сигналов
        self.process_trading_signals(pairs_data)

    def process_trading_signals(self, pairs_data):
        """Обработка торговых сигналов"""
        messages_to_send = []
        
        for pair_data in pairs_data:
            pair_name = pair_data.get('pair_name', 'UNKNOWN')
            current_signal = pair_data.get('signal', '')
            current_z = pair_data.get('z', 0)
            adf_passed = pair_data.get('adf_passed', False)
            
            if pair_name not in self.last_signals:
                self.last_signals[pair_name] = ''
                self.last_zs[pair_name] = 0
            
            should_send = False
            
            # Логика отправки сигналов
            if (current_signal != self.last_signals[pair_name] and 
                current_signal not in ["HOLD", "NO DATA", "NO TRADE - NOT STATIONARY"]):
                should_send = True
            elif (adf_passed and 
                  abs(current_z - self.last_zs[pair_name]) > 0.2 and
                  current_signal not in ["HOLD", "NO DATA"]):
                should_send = True
            elif (self.last_signals[pair_name] == '' and 
                  current_signal not in ["HOLD", "NO DATA", "NO TRADE - NOT STATIONARY"]):
                should_send = True
            
            if should_send:
                asset_a = pair_data.get('asset_a', 'UNKNOWN').split('/')[0]
                asset_b = pair_data.get('asset_b', 'UNKNOWN').split('/')[0]
                
                # Безопасное форматирование
                z_score = self.safe_format_number(current_z, precision=2)
                price_a = self.safe_format_number(pair_data.get('price_a', 0), precision=2)
                price_b = self.safe_format_number(pair_data.get('price_b', 0), precision=2)
                
                formatted_signal = current_signal
                if "SHORT_" in current_signal and "LONG_" in current_signal:
                    parts = current_signal.split('_')
                    if len(parts) >= 4:
                        formatted_signal = f"SHORT {parts[1]} / LONG {parts[3]}"
                
                msg = (
                    f"🎯 <b>TRADING SIGNAL - {pair_name}</b>\n"
                    f"Signal: <b>{formatted_signal}</b>\n"
                    f"Z-score: {z_score}\n"
                    f"ADF Test: {'✅ PASSED' if adf_passed else '❌ FAILED'}\n"
                    f"Prices: {asset_a}={price_a} | {asset_b}={price_b}"
                )
                
                messages_to_send.append({
                    'message': msg,
                    'signal': current_signal,
                    'pair_name': pair_name
                })
            
            # Обновляем последние значения
            self.last_signals[pair_name] = current_signal
            self.last_zs[pair_name] = current_z
        
        # Отправка собранных сигналов
        for msg_data in messages_to_send:
            buttons = None
            signal = msg_data['signal']
            pair_name = msg_data['pair_name']
            
            if signal and signal not in ["HOLD", "NO DATA", "NO TRADE - NOT STATIONARY", "EXIT_POSITION"]:
                buttons = [
                    [
                        {'text': '📈 OPEN', 'callback_data': f'OPEN:{signal}:{pair_name}'},
                        {'text': '📉 CLOSE', 'callback_data': f'CLOSE:{signal}:{pair_name}'}
                    ]
                ]
            elif signal == "EXIT_POSITION":
                buttons = [
                    [
                        {'text': '🔴 CLOSE POSITION', 'callback_data': f'CLOSE:{signal}:{pair_name}'}
                    ]
                ]
            
            self.send_message(msg_data['message'], buttons)

    def send_detailed_status(self, trader, data=None):
        """Детальный статус Paper Trading"""
        try:
            if trader is None:
                print("❌ Trader is None in send_detailed_status")
                return False
                
            summary = trader.get_trading_summary(data)
            if not summary:
                print("❌ Empty summary from trader")
                return False
            
            # Безопасное форматирование всех числовых значений
            initial_balance = self.safe_format_number(summary.get('initial_balance', 0))
            total_equity = self.safe_format_number(summary.get('total_equity', 0))
            total_pnl = self.safe_format_number(summary.get('total_pnl', 0))
            floating_pnl = self.safe_format_number(summary.get('floating_pnl', 0))
            total_trades = summary.get('total_trades', 0)
            open_positions = summary.get('open_positions', 0)
            win_rate = self.safe_format_number(summary.get('win_rate', 0), precision=1)
            max_drawdown = self.safe_format_number(summary.get('max_drawdown', 0), precision=1)
            
            # Основное сообщение со статусом
            main_msg = (
                f"📈 <b>PAPER TRADING STATUS</b>\n"
                f"Initial: ${initial_balance:.2f}\n"
                f"Equity: ${total_equity:.2f}\n"
                f"Closed PnL: ${total_pnl:.2f}\n"
                f"Floating PnL: ${floating_pnl:.2f}\n"
                f"Trades: {total_trades}\n"
                f"Open: {open_positions}\n"
                f"Win Rate: {win_rate:.1f}%\n"
                f"Drawdown: {max_drawdown:.1f}%\n"
            )
            
            # Детали открытых позиций
            positions_msg = ""
            open_positions_details = summary.get('open_positions_details', [])
            if open_positions_details:
                positions_msg = "\n\n🎯 <b>OPEN POSITIONS:</b>\n"
                for pos in open_positions_details:
                    entry_z = self.safe_format_number(pos.get('entry_z', 0), precision=2)
                    current_z = self.safe_format_number(pos.get('current_z'), precision=2)
                    floating_pnl_val = self.safe_format_number(pos.get('floating_pnl', 0), precision=2)
                    size = self.safe_format_number(pos.get('size', 0), precision=2)
                    duration = pos.get('duration_minutes', 0)
                    pair_name = pos.get('pair', 'UNKNOWN')
                    signal = pos.get('signal', 'N/A')
                    
                    # Определяем тренд и иконку
                    if current_z is not None:
                        if abs(current_z) < abs(entry_z):
                            trend = "📉 к выходу"
                            trend_arrow = "🟢"
                        else:
                            trend = "📈 от выхода" 
                            trend_arrow = "🔴"
                        z_change = current_z - entry_z
                    else:
                        trend = "📊 нет данных"
                        trend_arrow = "⚪"
                        z_change = 0
                    
                    positions_msg += (
                        f"{trend_arrow} <b>{pair_name}</b>\n"
                        f"   Signal: {signal}\n"
                        f"   Entry Z: {entry_z:.2f}\n"
                        f"   Current Z: {current_z:.2f if current_z is not None else 'N/A'}\n"
                        f"   Change: {z_change:+.2f} {trend}\n"
                        f"   PnL: ${floating_pnl_val:+.2f}\n"
                        f"   Size: ${size:.2f}\n"
                        f"   Duration: {duration} min\n"
                        f"   ───────────────────\n"
                    )
            else:
                positions_msg = "\n\n📋 <b>No open positions</b>"
            
            # Легенда для понимания сигналов
            legend_msg = (
                "\n\n📊 <b>LEGEND:</b>\n"
                "🟢 Z-score → 0 (хорошо)\n"
                "🔴 Z-score ← 0 (плохо)\n"
                "🎯 Вход: |Z| > 1.0, Выход: |Z| < 0.5"
            )
            
            # Кнопки управления
            buttons = [
                [
                    {'text': '📊 Summary', 'callback_data': 'SUMMARY'},
                    {'text': '🛑 Close All', 'callback_data': 'CLOSE_ALL'}
                ],
                [
                    {'text': '✅ Enable Auto', 'callback_data': 'ENABLE_AUTO'},
                    {'text': '🚫 Disable Auto', 'callback_data': 'DISABLE_AUTO'},
                    {'text': '💾 Export Log', 'callback_data': 'EXPORT_LOG'}
                ]
            ]
            
            full_msg = main_msg + positions_msg + legend_msg
            return self.send_message(full_msg, buttons)
            
        except Exception as e:
            print(f"❌ Error in send_detailed_status: {e}")
            return False

    def handle_management_callback(self, callback_data, trader, current_data=None):
        """Обработка callback'ов управления из Telegram"""
        try:
            if callback_data == 'SUMMARY':
                self.send_detailed_status(trader, current_data)
                
            elif callback_data == 'CLOSE_ALL':
                if trader:
                    closed_count = trader.close_all_positions()
                    self.send_message(f"✅ Closed {closed_count} positions")
                else:
                    self.send_message("❌ Trader not available")
                    
            elif callback_data == 'ENABLE_AUTO':
                if trader:
                    trader.enable_trading()
                    self.send_message("✅ Auto trading ENABLED")
                else:
                    self.send_message("❌ Trader not available")
                    
            elif callback_data == 'DISABLE_AUTO':
                if trader:
                    trader.disable_trading()
                    self.send_message("🚫 Auto trading DISABLED")
                else:
                    self.send_message("❌ Trader not available")
                    
            elif callback_data == 'EXPORT_LOG':
                if trader and trader.export_trading_log():
                    self.send_message("✅ Trading log exported")
                else:
                    self.send_message("❌ Failed to export log")
                    
        except Exception as e:
            error_msg = f"❌ Error handling callback {callback_data}: {e}"
            print(error_msg)
            self.send_message(error_msg)

    def send_simple_message(self, text):
        """Простая отправка текстового сообщения"""
        return self.send_message(text)

    def get_bot_info(self):
        """Получение информации о боте"""
        url = f"https://api.telegram.org/bot{self.token}/getMe"
        try:
            response = requests.get(url, timeout=10)
            return response.json()
        except Exception as e:
            print(f"❌ Error getting bot info: {e}")
            return None