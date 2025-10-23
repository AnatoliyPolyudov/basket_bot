import ccxt
import pandas as pd
import time
from datetime import datetime

class SpreadAnalyzer:
    def __init__(self):
        self.exchanges = {
            'binance': ccxt.binance(),
            'okx': ccxt.okx(),
            'bybit': ccxt.bybit(),
            'kucoin': ccxt.kucoin(),
            'gateio': ccxt.gateio(),
            'mexc': ccxt.mexc()
        }
        
        self.symbols = [
            'BTC/USDT', 'ETH/USDT', 'SOL/USDT',
            'XRP/USDT', 'ADA/USDT', 'DOT/USDT'
        ]

    def fetch_prices(self):
        """Получаем цены со всех бирж"""
        prices = {}
        
        for exchange_name, exchange in self.exchanges.items():
            try:
                prices[exchange_name] = {}
                print(f"🔍 Загружаем данные с {exchange_name}...")
                
                for symbol in self.symbols:
                    try:
                        ticker = exchange.fetch_ticker(symbol)
                        prices[exchange_name][symbol] = {
                            'bid': ticker['bid'],
                            'ask': ticker['ask'],
                            'last': ticker['last'],
                            'spread_pct': (ticker['ask'] - ticker['bid']) / ticker['bid'] * 100
                        }
                    except Exception as e:
                        print(f"   Ошибка для {symbol} на {exchange_name}: {e}")
                
                time.sleep(0.2)  # Rate limit
            except Exception as e:
                print(f"❌ Ошибка подключения к {exchange_name}: {e}")
                
        return prices

    def calculate_arbitrage_opportunities(self, prices):
        """Рассчитываем арбитражные возможности"""
        opportunities = []
        
        for symbol in self.symbols:
            best_bid = {'exchange': None, 'price': 0}
            best_ask = {'exchange': None, 'price': float('inf')}
            
            for exchange_name in prices:
                if symbol in prices[exchange_name]:
                    price_data = prices[exchange_name][symbol]
                    
                    if price_data['ask'] < best_ask['price']:
                        best_ask = {'exchange': exchange_name, 'price': price_data['ask']}
                    
                    if price_data['bid'] > best_bid['price']:
                        best_bid = {'exchange': exchange_name, 'price': price_data['bid']}
            
            if (best_bid['exchange'] and best_ask['exchange'] and 
                best_bid['exchange'] != best_ask['exchange']):
                
                spread_pct = (best_bid['price'] - best_ask['price']) / best_ask['price'] * 100
                
                if spread_pct > 0.05:  # Минимальный спред 0.05%
                    opportunities.append({
                        'symbol': symbol,
                        'buy_at': best_ask['exchange'],
                        'sell_at': best_bid['exchange'],
                        'buy_price': best_ask['price'],
                        'sell_price': best_bid['price'],
                        'spread_pct': spread_pct,
                        'profit_per_unit': best_bid['price'] - best_ask['price'],
                        'timestamp': datetime.now()
                    })
        
        return sorted(opportunities, key=lambda x: x['spread_pct'], reverse=True)

    def analyze_commissions_impact(self, opportunity, capital=1000):
        """Анализ влияния комиссий на прибыль"""
        commissions = {
            'binance': 0.1,
            'okx': 0.08,
            'bybit': 0.06,
            'kucoin': 0.1,
            'gateio': 0.2,
            'mexc': 0.2
        }
        
        buy_commission = commissions.get(opportunity['buy_at'], 0.1)
        sell_commission = commissions.get(opportunity['sell_at'], 0.1)
        
        units = capital / opportunity['buy_price']
        gross_profit = units * opportunity['profit_per_unit']
        total_commissions = capital * (buy_commission + sell_commission) / 100
        
        net_profit = gross_profit - total_commissions
        net_profit_pct = (net_profit / capital) * 100
        
        return {
            'gross_profit': gross_profit,
            'total_commissions': total_commissions,
            'net_profit': net_profit,
            'net_profit_pct': net_profit_pct,
            'profitable': net_profit > 0
        }

    def monitor_continuous(self, interval=30):
        """Непрерывный мониторинг"""
        print("🚀 ЗАПУСК АНАЛИЗА СПРЕДОВ МЕЖДУ БИРЖАМИ...")
        print("=" * 80)
        
        while True:
            try:
                print(f"\n📊 {datetime.now().strftime('%H:%M:%S')} - Обновление данных...")
                prices = self.fetch_prices()
                opportunities = self.calculate_arbitrage_opportunities(prices)
                
                if opportunities:
                    print(f"\n🎯 НАЙДЕНО АРБИТРАЖНЫХ ВОЗМОЖНОСТЕЙ: {len(opportunities)}")
                    print("=" * 80)
                    
                    for i, opp in enumerate(opportunities[:5], 1):
                        profit_analysis = self.analyze_commissions_impact(opp)
                        
                        print(f"\n#{i} {opp['symbol']}")
                        print(f"   📈 КУПИТЬ:  {opp['buy_at']:8} @ ${opp['buy_price']:.4f}")
                        print(f"   📉 ПРОДАТЬ: {opp['sell_at']:8} @ ${opp['sell_price']:.4f}")
                        print(f"   📊 Спред: {opp['spread_pct']:.4f}%")
                        print(f"   💰 Прибыль за единицу: ${opp['profit_per_unit']:.4f}")
                        
                        if profit_analysis['profitable']:
                            print(f"   ✅ ЧИСТАЯ ПРИБЫЛЬ: ${profit_analysis['net_profit']:.2f} ({profit_analysis['net_profit_pct']:.4f}%)")
                        else:
                            print(f"   ❌ УБЫТОК: ${abs(profit_analysis['net_profit']):.2f} (комиссии съедают прибыль)")
                else:
                    print("\n❌ Арбитражные возможности не найдены (спреды слишком маленькие)")
                
                # Сводка по спредам
                print(f"\n📋 СВОДКА ПО СПРЕДАМ:")
                for symbol in self.symbols[:3]:  # Только первые 3 для краткости
                    print(f"\n{symbol}:")
                    for exchange in ['binance', 'okx', 'bybit']:
                        if exchange in prices and symbol in prices[exchange]:
                            spread = prices[exchange][symbol]['spread_pct']
                            print(f"   {exchange:8}: {spread:.4f}%")
                
                print(f"\n⏳ Следующее обновление через {interval} секунд...")
                print("=" * 80)
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n🛑 Мониторинг остановлен пользователем")
                break
            except Exception as e:
                print(f"❌ Ошибка: {e}")
                time.sleep(30)

# Запуск анализатора
if __name__ == "__main__":
    analyzer = SpreadAnalyzer()
    analyzer.monitor_continuous(interval=30)
