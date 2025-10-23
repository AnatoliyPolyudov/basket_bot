import ccxt
import time
import pandas as pd
from datetime import datetime

class FundingArbitrageMonitor:
    def __init__(self):
        self.exchanges = {
            'binance': ccxt.binance({'options': {'defaultType': 'future'}}),
            'bybit': ccxt.bybit({'options': {'defaultType': 'future'}}),
            'okx': ccxt.okx({'options': {'defaultType': 'future'}}),
            'gate': ccxt.gateio({'options': {'defaultType': 'future'}})
        }
        
        self.symbols = ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT"]
        self.min_spread = 0.0003  # 0.03%
        self.opportunities_history = []

    def fetch_funding_rates(self):
        """Получаем funding rates со всех бирж"""
        funding_data = {}
        
        for exchange_name, exchange in self.exchanges.items():
            try:
                funding_data[exchange_name] = {}
                for symbol in self.symbols:
                    funding = exchange.fetch_funding_rate(symbol)
                    funding_data[exchange_name][symbol] = {
                        'rate': funding['fundingRate'],
                        'next_funding': funding['nextFundingTime'],
                        'timestamp': funding['timestamp']
                    }
                time.sleep(0.1)  # Rate limit
            except Exception as e:
                print(f"Ошибка на {exchange_name}: {e}")
                
        return funding_data

    def find_arbitrage_opportunities(self, funding_data):
        """Находим арбитражные возможности"""
        opportunities = []
        
        for symbol in self.symbols:
            rates = {}
            
            # Собираем rates для всех бирж
            for exchange_name in funding_data:
                if symbol in funding_data[exchange_name]:
                    rates[exchange_name] = funding_data[exchange_name][symbol]['rate']
            
            if len(rates) >= 2:
                # Находим максимальную и минимальную ставку
                max_exchange = max(rates, key=rates.get)
                min_exchange = min(rates, key=rates.get)
                spread = rates[max_exchange] - rates[min_exchange]
                
                if abs(spread) > self.min_spread:
                    opportunity = {
                        'symbol': symbol,
                        'long_exchange': min_exchange,   # LOW funding - покупаем тут
                        'short_exchange': max_exchange,  # HIGH funding - шортим тут
                        'spread': spread,
                        'long_rate': rates[min_exchange],
                        'short_rate': rates[max_exchange],
                        'timestamp': datetime.now(),
                        'profit_potential': abs(spread) * 100  # в процентах
                    }
                    opportunities.append(opportunity)
                    self.opportunities_history.append(opportunity)
        
        return opportunities

    def calculate_profitability(self, opportunity, capital=1000):
        """Расчет реальной прибыли с учетом комиссий"""
        # Комиссии (0.1% на биржах)
        total_commissions = capital * 0.002  # 0.2% за круг
        
        # Прибыль от funding за 8 часов
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

    def monitor_continuous(self, interval=300):
        """Непрерывный мониторинг"""
        print("🚀 Starting Cross-Exchange Funding Arbitrage Monitor...")
        print("=" * 70)
        
        while True:
            try:
                funding_data = self.fetch_funding_rates()
                opportunities = self.find_arbitrage_opportunities(funding_data)
                
                current_time = datetime.now().strftime('%H:%M:%S')
                print(f"\n📊 {current_time} - Найдено возможностей: {len(opportunities)}")
                
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
                
                if not opportunities:
                    print("   🤷 No arbitrage opportunities found")
                
                print(f"\n⏳ Next check in {interval//60} minutes...")
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n🛑 Monitoring stopped by user")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                time.sleep(60)

# Запуск монитора
if __name__ == "__main__":
    monitor = FundingArbitrageMonitor()
    monitor.monitor_continuous()