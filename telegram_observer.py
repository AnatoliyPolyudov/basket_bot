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
        self.last_signals = {}  # 🆕 Храним последние сигналы для каждой пары
        self.last_zs = {}       # 🆕 Храним последние Z-score для каждой пары

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
        # 🆕 ОБРАБАТЫВАЕМ ДАННЫЕ ОТ НОВОГО R-ПОДХОДА
        pairs_data = data.get('pairs_data', [])
        
        # 🆕 ФИЛЬТРАЦИЯ: отправляем только важные изменения по парам
        messages_to_send = []
        
        for pair_data in pairs_data:
            pair_name = pair_data['pair_name']
            current_signal = pair_data.get('signal', '')
            current_z = pair_data.get('z', 0)
            adf_passed = pair_data.get('adf_passed', False)
            
            # Инициализируем пару если ее нет в истории
            if pair_name not in self.last_signals:
                self.last_signals[pair_name] = ''
                self.last_zs[pair_name] = 0
            
            # Проверяем нужно ли отправлять сообщение для этой пары
            should_send = False
            
            # 1. Сигнал изменился И это торговый сигнал
            if (current_signal != self.last_signals[pair_name] and 
                current_signal not in ["HOLD", "NO DATA", "NO TRADE - NOT STATIONARY"]):
                should_send = True
            
            # 2. Сильное изменение Z-score (более чем на 0.2) И ADF пройден
            elif (adf_passed and 
                  abs(current_z - self.last_zs[pair_name]) > 0.2 and
                  current_signal not in ["HOLD", "NO DATA"]):
                should_send = True
            
            # 3. Первое сообщение для пары с торговым сигналом
            elif (self.last_signals[pair_name] == '' and 
                  current_signal not in ["HOLD", "NO DATA", "NO TRADE - NOT STATIONARY"]):
                should_send = True
            
            if should_send:
                # Формируем сообщение для пары
                asset_a = pair_data['asset_a'].split('/')[0]  # BTC, ETH, etc
                asset_b = pair_data['asset_b'].split('/')[0]
                
                z_score = round(current_z, 2)
                spread = round(pair_data.get('spread', 0), 3)
                price_a = round(pair_data.get('price_a', 0), 2)
                price_b = round(pair_data.get('price_b', 0), 2)
                
                # 🆕 Форматируем сигнал для читаемости
                formatted_signal = current_signal
                if "SHORT_" in current_signal and "LONG_" in current_signal:
                    # Преобразуем "SHORT_ETH_LONG_BNB" в "SHORT ETH / LONG BNB"
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
            
            # Обновляем последние значения для пары
            self.last_signals[pair_name] = current_signal
            self.last_zs[pair_name] = current_z
        
        # 🆕 Отправляем сообщения с кнопками для каждой пары
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
        
        # 🆕 Отправляем сводку если есть активные пары
        active_pairs = data.get('active_pairs', 0)
        total_pairs = data.get('total_pairs', 0)
        
        if active_pairs > 0 and len(messages_to_send) > 0:
            summary_msg = f"\n📊 <b>SUMMARY:</b> {active_pairs}/{total_pairs} pairs stationary"
            self.send_message(summary_msg)

    # 🆕 Дополнительный метод для отправки общего статуса
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