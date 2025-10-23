import ccxt
import time
import pandas as pd
from datetime import datetime

class FundingArbitrageMonitor:
    def __init__(self):
        self.exchanges = {
            'binance': ccxt.binance({'options': {'defaultType': 'future'}}),
            'bybit': ccxt.bybit({'options': {'defaultType': 'future'}}),
            'okx': ccxt.okx({'options': {'defaultType': 'swap'}}),
            'gate': ccxt.gateio({'options': {'defaultType': 'future'}}),
            'mexc': ccxt.mexc({'options': {'defaultType': 'future'}})
        }
        
        # ПРАВИЛЬНЫЕ СИМВОЛЫ ДЛЯ КАЖДОЙ БИРЖИ
        self.symbols_map = {
            'binance': ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
            'bybit': ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT"],
            'okx': ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT"],
            'gate': ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
            'mexc': ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
        }
        
        self.min_spread = 0.0003  # 0.03%
        self.opportunities_history = []

    def safe_fetch_funding_rate(self, exchange, exchange_name, symbol):
        """Безопасное получение funding rate"""
        try:
            funding_data = exchange.fetch_funding_rate(symbol)
            
            if isinstance(funding_data, dict) and 'fundingRate' in funding_data:
                rate = funding_data['fundingRate']
                next_time = funding_data.get('nextFundingTime', 'N/A')
                timestamp = funding_data.get('timestamp', exchange.milliseconds())
                
                return {
                    'rate': float(rate),
                    'next_funding': next_time,
                    'timestamp': timestamp
                }
                    
        except Exception as e:
            print(f"    ❌ {symbol}: {str(e)[:80]}")  # Обрезаем длинные ошибки
            
        return None

    def fetch_funding_rates(self):
        """Получаем funding rates со всех бирж"""
        funding_data = {}
        
        for exchange_name, exchange in self.exchanges.items():
            try:
                print(f"🔍 Загружаем данные с {exchange_name}...")
                funding_data[exchange_name] = {}
                
                symbols = self.symbols_map.get(exchange_name, [])
                
                for symbol in symbols:
                    result = self.safe_fetch_funding_rate(exchange, exchange_name, symbol)
                    if result:
                        funding_data[exchange_name][symbol] = result
                        print(f"    ✅ {symbol}: {result['rate']:.6f}")
                    else:
                        print(f"    ❌ {symbol}: не удалось получить данные")
                    
                    time.sleep(0.3)  # Rate limit
                    
            except Exception as e:
                print(f"❌ Ошибка подключения к {exchange_name}: {e}")
                
        return funding_data

    def normalize_symbol(self, symbol):
        """Нормализуем символ для сравнения между биржами"""
        return symbol.replace(':USDT', '').replace('/USDT', '')

    def find_arbitrage_opportunities(self, funding_data):
        """Находим арбитражные возможности"""
        opportunities = []
        
        # Создаем единый список символов для сравнения
        all_rates = {}
        
        for exchange_name in funding_data:
            for symbol in funding_data[exchange_name]:
                normalized_symbol = self.normalize_symbol(symbol)
                if normalized_symbol not in all_rates:
                    all_rates[normalized_symbol] = {}
                
                rate_data = funding_data[exchange_name][symbol]
                all_rates[normalized_symbol][exchange_name] = rate_data['rate']
        
        # Ищем арбитражные возможности
        for symbol, rates in all_rates.items():
            if len(rates) >= 2:
                max_exchange = max(rates, key=rates.get)
                min_exchange = min(rates, key=rates.get)
                spread = rates[max_exchange] - rates[min_exchange]
                
                if abs(spread) > self.min_spread:
                    opportunity = {
                        'symbol': symbol,
                        'long_exchange': min_exchange,
                        'short_exchange': max_exchange,
                        'spread': spread,
                        'long_rate': rates[min_exchange],
                        'short_rate': rates[max_exchange],
                        'timestamp': datetime.now(),
                        'profit_potential': abs(spread) * 100
                    }
                    opportunities.append(opportunity)
                    self.opportunities_history.append(opportunity)
        
        return opportunities

    def calculate_profitability(self, opportunity, capital=1000):
        """Расчет реальной прибыли с учетом комиссий"""
        total_commissions = capital * 0.002  # 0.2% за круг
        funding_profit = capital * abs(opportunity['spread'])
        net_profit = funding_profit - total_commissions
        roi_per_period = (net_profit / capital) * 100
        
        return {
            'capital': capital,
            'funding_profit': funding_profit,
            'commissions': total_commissions,
            'net_profit': net_profit,
            'roi_per_period': roi_per_period,
            'profitable': net_profit > 0
        }

    def monitor_continuous(self, interval=60):
        """Непрерывный мониторинг"""
        print("🚀 Starting Cross-Exchange Funding Arbitrage Monitor...")
        print("=" * 70)
        
        while True:
            try:
                funding_data = self.fetch_funding_rates()
                opportunities = self.find_arbitrage_opportunities(funding_data)
                
                current_time = datetime.now().strftime('%H:%M:%S')
                print(f"\n📊 {current_time} - Найдено возможностей: {len(opportunities)}")
                
                if opportunities:
                    for opp in opportunities:
                        profit_data = self.calculate_profitability(opp)
                        
                        print(f"\n🎯 {opp['symbol']}")
                        print(f"   LONG:  {opp['long_exchange']} ({opp['long_rate']:.6f})")
                        print(f"   SHORT: {opp['short_exchange']} ({opp['short_rate']:.6f})")
                        print(f"   Spread: {opp['spread']:.6f} ({opp['profit_potential']:.4f}%)")
                        
                        if profit_data['profitable']:
                            print(f"   ✅ PROFIT: ${profit_data['net_profit']:.2f} (ROI: {profit_data['roi_per_period']:.4f}%)")
                        else:
                            print(f"   ❌ LOSS: ${abs(profit_data['net_profit']):.2f} (комиссии)")
                else:
                    print("   🤷 No arbitrage opportunities found")
                    print("   💡 Попробуйте увеличить min_spread или добавить больше бирж")
                
                print(f"\n⏳ Next check in {interval} seconds...")
                print("=" * 70)
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n🛑 Monitoring stopped by user")
                break
            except Exception as e:
                print(f"❌ Error in main loop: {e}")
                time.sleep(30)

# Запуск монитора
if __name__ == "__main__":
    monitor = FundingArbitrageMonitor()
    monitor.monitor_continuous()