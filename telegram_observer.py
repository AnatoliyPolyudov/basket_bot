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
            return True
        except Exception as e:
            print(f"❌ Telegram send failed: {e}")
            return False

    def update(self, data):
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
            pair_name = pair_data['pair_name']
            current_signal = pair_data.get('signal', '')
            current_z = pair_data.get('z', 0)
            adf_passed = pair_data.get('adf_passed', False)
            
            if pair_name not in self.last_signals:
                self.last_signals[pair_name] = ''
                self.last_zs[pair_name] = 0
            
            should_send = False
            
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
                asset_a = pair_data['asset_a'].split('/')[0]
                asset_b = pair_data['asset_b'].split('/')[0]
                
                # Безопасное форматирование
                try:
                    z_score = round(float(current_z), 2) if current_z is not None else 0
                except (ValueError, TypeError):
                    z_score = current_z
                
                try:
                    price_a = round(float(pair_data.get('price_a', 0)), 2) if pair_data.get('price_a') is not None else 0
                    price_b = round(float(pair_data.get('price_b', 0)), 2) if pair_data.get('price_b') is not None else 0
                except (ValueError, TypeError):
                    price_a = pair_data.get('price_a', 0)
                    price_b = pair_data.get('price_b', 0)
                
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
            
            self.last_signals[pair_name] = current_signal
            self.last_zs[pair_name] = current_z
        
        # Отправка сигналов
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
                return False
                
            summary = trader.get_trading_summary(data)
            
            main_msg = (
                f"📈 <b>PAPER TRADING STATUS</b>\n"
                f"Initial: ${summary.get('initial_balance', 0):.2f}\n"
                f"Equity: ${summary.get('total_equity', 0):.2f}\n"
                f"Closed PnL: ${summary.get('total_pnl', 0):.2f}\n"
                f"Floating PnL: ${summary.get('floating_pnl', 0):.2f}\n"
                f"Trades: {summary.get('total_trades', 0)}\n"
                f"Open: {summary.get('open_positions', 0)}\n"
                f"Win Rate: {summary.get('win_rate', 0):.1f}%\n"
                f"Drawdown: {summary.get('max_drawdown', 0):.1f}%\n"
            )
            
            positions_msg = ""
            if 'open_positions_details' in summary and summary['open_positions_details']:
                positions_msg = "\n\n🎯 <b>OPEN POSITIONS:</b>\n"
                for pos in summary['open_positions_details']:
                    entry_z = pos['entry_z']
                    current_z = pos['current_z']
                    
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
                        f"{trend_arrow} <b>{pos['pair']}</b>\n"
                        f"   Signal: {pos['signal']}\n"
                        f"   Entry Z: {entry_z:.2f}\n"
                        f"   Current Z: {current_z:.2f if current_z is not None else 'N/A'}\n"
                        f"   Change: {z_change:+.2f} {trend}\n"
                        f"   PnL: ${pos['floating_pnl']:+.2f}\n"
                        f"   Size: ${pos['size']:.2f}\n"
                        f"   Duration: {pos['duration_minutes']} min\n"
                        f"   ───────────────────\n"
                    )
            else:
                positions_msg = "\n\n📋 <b>No open positions</b>"
            
            legend_msg = (
                "\n\n📊 <b>LEGEND:</b>\n"
                "🟢 Z-score → 0 (хорошо)\n"
                "🔴 Z-score ← 0 (плохо)\n"
                "🎯 Вход: |Z| > 1.0, Выход: |Z| < 0.5"
            )
            
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
        if callback_data == 'SUMMARY':
            self.send_detailed_status(trader, current_data)
        elif callback_data == 'CLOSE_ALL':
            closed_count = trader.close_all_positions()
            self.send_message(f"✅ Closed {closed_count} positions")
        elif callback_data == 'ENABLE_AUTO':
            trader.enable_trading()
            self.send_message("✅ Auto trading ENABLED")
        elif callback_data == 'DISABLE_AUTO':
            trader.disable_trading()
            self.send_message("🚫 Auto trading DISABLED")
        elif callback_data == 'EXPORT_LOG':
            if trader.export_trading_log():
                self.send_message("✅ Trading log exported")
            else:
                self.send_message("❌ Failed to export log")