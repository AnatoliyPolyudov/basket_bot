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
            requests.post(url, data=payload, timeout=10)
            print("Telegram message sent")
        except Exception as e:
            print("Telegram send failed:", e)

    def update(self, data):
        pairs_data = data.get('pairs_data', [])
        
        # 🆕 ОТПРАВЛЯЕМ СТАТУС ПОЗИЦИЙ КАЖДЫЕ 10 МИНУТ
        current_time = datetime.now()
        if (not self.last_status_message or 
            (current_time - self.last_status_message).total_seconds() > 600):
            
            status_msg = self.generate_positions_status()
            if status_msg:
                self.send_message(status_msg)
                self.last_status_message = current_time
        
        # Обработка торговых сигналов (существующий код)
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
                
                z_score = round(current_z, 2)
                spread = round(pair_data.get('spread', 0), 3)
                price_a = round(pair_data.get('price_a', 0), 2)
                price_b = round(pair_data.get('price_b', 0), 2)
                
                formatted_signal = current_signal
                if "SHORT_" in current_signal and "LONG_" in current_signal:
                    parts = current_signal.split('_')
                    if len(parts) >= 4:
                        formatted_signal = f"SHORT {parts[1]} / LONG {parts[3]}"
                
                msg = (
                    f"🎯 <b>PAIR TRADING ALERT - {pair_name}</b>\n"
                    f"Signal: <b>{formatted_signal}</b>\n"
                    f"Z-score: {z_score}\n"
                    f"Spread: {spread}\n"
                    f"ADF Test: {'✅ PASSED' if adf_passed else '❌ FAILED'}\n"
                    f"Prices: {asset_a}={price_a} | {asset_b}={price_b}\n"
                    f"Pair: {asset_a} / {asset_b}"
                )
                
                messages_to_send.append({
                    'message': msg,
                    'signal': current_signal,
                    'pair_name': pair_name
                })
            
            self.last_signals[pair_name] = current_signal
            self.last_zs[pair_name] = current_z
        
        for msg_data in messages_to_send:
            buttons = None
            signal = msg_data['signal']
            pair_name = msg_data['pair_name']
            
            if signal and signal not in ["HOLD", "NO DATA", "NO TRADE - NOT STATIONARY", "EXIT_POSITION"]:
                buttons = [
                    [
                        {'text': 'OPEN', 'callback_data': f'OPEN:{signal}:{pair_name}'},
                        {'text': 'CLOSE', 'callback_data': f'CLOSE:{signal}:{pair_name}'}
                    ]
                ]
            elif signal == "EXIT_POSITION":
                buttons = [
                    [
                        {'text': 'CLOSE POSITION', 'callback_data': f'CLOSE:{signal}:{pair_name}'}
                    ]
                ]
            
            self.send_message(msg_data['message'], buttons)

    # 🆕 МЕТОД ДЛЯ СТАТУСА ПОЗИЦИЙ
    def generate_positions_status(self):
        """Генерирует статус открытых позиций"""
        if not self.trader:
            return None
            
        open_positions = self.trader.get_open_positions()
        if not open_positions:
            return None
            
        summary = self.trader.get_trading_summary()
        
        msg = (
            f"📊 <b>PAPER TRADING STATUS</b>\n"
            f"Balance: ${summary['current_balance']:.2f}\n"
            f"Equity: ${summary['total_equity']:.2f}\n"
            f"Floating PnL: ${summary['floating_pnl']:.2f}\n"
            f"Open Positions: {summary['open_positions']}\n"
            f"Win Rate: {summary['win_rate']:.1f}%\n"
            f"Max Drawdown: {summary['max_drawdown']:.1f}%\n"
            f"────────────────────\n"
        )
        
        for pair_name, position in open_positions.items():
            duration = (datetime.now() - position['entry_time']).total_seconds() / 60
            msg += (
                f"🎯 <b>{pair_name}</b>\n"
                f"Signal: {position['signal']}\n"
                f"Size: ${position['size']:.2f}\n"
                f"PnL: ${position['floating_pnl']:.2f}\n"
                f"Entry Z: {position['entry_z']:.2f}\n"
                f"Duration: {duration:.1f} min\n"
                f"Type: {position['type']}\n"
                f"────────────────────\n"
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
        
        self.send_message(msg, buttons)
        return msg

    # 🆕 ОБРАБОТКА CALLBACK ДЛЯ УПРАВЛЕНИЯ
    def handle_management_callback(self, callback_data, trader):
        """Обработка callback для управления торговлей"""
        if callback_data == 'SUMMARY':
            summary = trader.get_trading_summary()
            msg = (
                f"📈 <b>TRADING SUMMARY</b>\n"
                f"Initial Balance: ${summary['initial_balance']:.2f}\n"
                f"Current Equity: ${summary['total_equity']:.2f}\n"
                f"Total PnL: ${summary['total_pnl']:.2f}\n"
                f"Floating PnL: ${summary['floating_pnl']:.2f}\n"
                f"Total Trades: {summary['total_trades']}\n"
                f"Open Positions: {summary['open_positions']}\n"
                f"Win Rate: {summary['win_rate']:.1f}%\n"
                f"Max Drawdown: {summary['max_drawdown']:.1f}%\n"
                f"Best Trade: ${summary['best_trade']:.2f}\n"
                f"Worst Trade: ${summary['worst_trade']:.2f}\n"
                f"Avg Duration: {summary['avg_duration']:.1f} min"
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
            
        elif callback_data == 'EXPORT_LOG':
            if trader.export_trading_log():
                self.send_message("✅ Trading log exported successfully")
            else:
                self.send_message("❌ Failed to export trading log")

    def send_status_summary(self, pairs_data):
        """Отправка общего статуса всех пар"""
        active_count = sum(1 for p in pairs_data if p.get('adf_passed', False))
        trading_signals = [p for p in pairs_data if p.get('signal') not in ["HOLD", "NO DATA", "NO TRADE - NOT STATIONARY"]]
        
        msg = (
            f"📈 <b>PAIRS STATUS SUMMARY</b>\n"
            f"Active Pairs: {active_count}/{len(pairs_data)}\n"
            f"Trading Signals: {len(trading_signals)}\n"
        )
        
        for pair in pairs_data:
            if pair.get('adf_passed', False):
                signal = pair.get('signal', 'HOLD')
                z_score = round(pair.get('z', 0), 2)
                msg += f"\n{pair['pair_name']}: {signal} (Z={z_score})"
        
        self.send_message(msg)