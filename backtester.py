# backtester.py - ТЕСТ ТОП-20 ПАР
import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse
from pairs_core import PairAnalyzer
from statsmodels.tsa.stattools import adfuller
import time

def fetch_historical_data(symbol: str, days: int = 365) -> pd.Series:
    """Загрузка исторических данных с OKX"""
    try:
        exchange = ccxt.okx({"enableRateLimit": True})
        ohlcv = exchange.fetch_ohlcv(symbol, '1d', limit=min(days, 365))
        
        dates = [pd.Timestamp(x[0], unit='ms') for x in ohlcv]
        closes = [x[4] for x in ohlcv]
        
        return pd.Series(closes, index=dates, name=symbol)
        
    except Exception as e:
        print(f"❌ Error loading {symbol}: {e}")
        return pd.Series()

def is_pair_cointegrated(spread_data, critical_value=-2.58):
    """ADF тест как в R - тройная проверка"""
    if len(spread_data) < 120:
        return False
        
    try:
        adf_120 = adfuller(spread_data[-120:], maxlag=1, regression='c', autolag=None)[0]
        if adf_120 > critical_value: return False
            
        adf_90 = adfuller(spread_data[-90:], maxlag=1, regression='c', autolag=None)[0]
        if adf_90 > critical_value: return False
            
        adf_60 = adfuller(spread_data[-60:], maxlag=1, regression='c', autolag=None)[0]
        if adf_60 > critical_value: return False
            
        return True
        
    except Exception as e:
        return False

def run_single_backtest(pair_name: str, target_pair: dict, days: int = 180, adf_test: bool = True):
    """Бэктест одной пары"""
    print(f"\n🔍 Testing {pair_name}...")
    
    # Загружаем данные
    prices_a = fetch_historical_data(target_pair['asset_a'], days)
    prices_b = fetch_historical_data(target_pair['asset_b'], days)
    
    if prices_a.empty or prices_b.empty:
        print(f"❌ Failed to load data for {pair_name}")
        return None
    
    aligned_data = pd.DataFrame({
        'price_a': prices_a,
        'price_b': prices_b
    }).dropna()
    
    if len(aligned_data) < 130:
        print(f"❌ Not enough data for {pair_name}: {len(aligned_data)} days")
        return None
    
    aligned_data['spread'] = aligned_data['price_a'] / aligned_data['price_b']
    
    # Параметры
    entry_z, exit_z = 1.0, 0.5
    stop_loss, max_hold_days, commission = 0.10, 30, 0.002
    
    # Бэктестинг
    returns = []
    positions = []
    entry_prices = {}
    
    for i in range(130, len(aligned_data)):
        window = aligned_data['spread'].iloc[i-35:i]
        current_spread = aligned_data['spread'].iloc[i]
        
        if window.std() > 0:
            z_score = (current_spread - window.mean()) / window.std()
        else:
            z_score = 0
        
        # ADF проверка
        can_trade = True
        if adf_test:
            spread_history = aligned_data['spread'].iloc[:i+1]
            can_trade = is_pair_cointegrated(spread_history)
        
        # Текущая позиция
        current_position = positions[-1] if positions else 0
        
        # ПРОВЕРКА РИСК-МЕНЕДЖМЕНТА
        force_exit = False
        force_exit_reason = ""
        
        if current_position != 0:
            entry_spread, entry_idx = entry_prices.get(current_position, (0, 0))
            days_in_position = i - entry_idx
            
            # Расчет текущего PnL
            if current_position == 1:
                current_pnl = (current_spread - entry_spread) / entry_spread
            else:
                current_pnl = (entry_spread - current_spread) / entry_spread
            
            if current_pnl <= -stop_loss:
                force_exit = True
                force_exit_reason = f"STOP LOSS ({current_pnl*100:.1f}%)"
            elif days_in_position >= max_hold_days:
                force_exit = True
                force_exit_reason = f"MAX HOLD DAYS ({days_in_position} days)"
        
        # ЛОГИКА ТРЕЙДИНГА (ТОЛЬКО ЕСЛИ ADF ПРОЙДЕН)
        if force_exit:
            # Принудительный выход
            entry_spread, entry_idx = entry_prices[current_position]
            exit_spread = current_spread
            
            if current_position == 1:
                pnl = (exit_spread - entry_spread) / entry_spread
            else:
                pnl = (entry_spread - exit_spread) / entry_spread
            
            pnl -= commission
            returns.append(pnl)
            
            print(f"   🛑 {force_exit_reason}")
            print(f"      PnL: {pnl*100:+.2f}%")
            
            del entry_prices[current_position]
            positions.append(0)
            
        elif current_position == 0 and can_trade:  # Нет позиции И ADF пройден
            if z_score > entry_z:
                positions.append(-1)
                entry_prices[-1] = (current_spread, i)
                print(f"   📈 ENTRY SHORT: Z = {z_score:.2f}")
            elif z_score < -entry_z:
                positions.append(1)
                entry_prices[1] = (current_spread, i)
                print(f"   📈 ENTRY LONG: Z = {z_score:.2f}")
            else:
                positions.append(0)
                
        elif current_position == 1 and can_trade:  # Long позиция И ADF пройден
            if z_score > -exit_z:
                entry_spread, entry_idx = entry_prices[1]
                exit_spread = current_spread
                
                pnl = (exit_spread - entry_spread) / entry_spread
                pnl -= commission
                
                returns.append(pnl)
                print(f"   📉 EXIT LONG: Z = {z_score:.2f}, PnL: {pnl*100:+.2f}%")
                
                del entry_prices[1]
                positions.append(0)
            else:
                positions.append(1)
                
        elif current_position == -1 and can_trade:  # Short позиция И ADF пройден
            if z_score < exit_z:
                entry_spread, entry_idx = entry_prices[-1]
                exit_spread = current_spread
                
                pnl = (entry_spread - exit_spread) / entry_spread
                pnl -= commission
                
                returns.append(pnl)
                print(f"   📉 EXIT SHORT: Z = {z_score:.2f}, PnL: {pnl*100:+.2f}%")
                
                del entry_prices[-1]
                positions.append(0)
            else:
                positions.append(-1)
        else:
            # Не торгуем - ADF не пройден или нет позиции
            positions.append(current_position)
    
    # Результаты для одной пары
    if returns:
        returns_series = pd.Series(returns)
        total_return = (returns_series + 1).prod() - 1
        win_rate = (returns_series > 0).mean() * 100
        
        return {
            'pair': pair_name,
            'total_return': total_return,
            'win_rate': win_rate,
            'trades': len(returns),
            'avg_return': returns_series.mean(),
            'best_trade': returns_series.max(),
            'worst_trade': returns_series.min()
        }
    
    return None

def run_all_backtests(days: int = 180, adf_test: bool = True, min_trades: int = 3, limit: int = 20):
    """Автоматический тест ТОП-20 пар"""
    analyzer = PairAnalyzer(n_pairs=100)  # 👈 Берем из 100 возможных
    
    # 👇 ОГРАНИЧИВАЕМ ТОП-20 ПАР
    pairs_to_test = analyzer.pairs[:limit]
    
    print(f"🚀 Testing TOP {len(pairs_to_test)} pairs (of {len(analyzer.pairs)} available)...")
    print(f"   Days: {days}, ADF Test: {adf_test}, Min Trades: {min_trades}")
    print("=" * 60)
    
    results = []
    
    for i, pair in enumerate(pairs_to_test):
        print(f"\n📊 {i+1}/{len(pairs_to_test)}: {pair['name']}")
        
        result = run_single_backtest(pair['name'], pair, days, adf_test)
        
        if result and result['trades'] >= min_trades:
            results.append(result)
            
            status = "✅ PROFITABLE" if result['total_return'] > 0 else "❌ UNPROFITABLE"
            print(f"   {status} | Return: {result['total_return']*100:+.2f}% | Win Rate: {result['win_rate']:.1f}% | Trades: {result['trades']}")
        else:
            print(f"   ⏩ SKIPPED | Not enough trades or data")
    
    # Сортировка результатов
    results.sort(key=lambda x: x['total_return'], reverse=True)
    
    # Вывод лучших пар
    print(f"\n{'='*60}")
    print(f"🎯 BEST PERFORMING PAIRS (Top 10)")
    print(f"{'='*60}")
    
    profitable_count = 0
    for i, result in enumerate(results[:10]):
        if result['total_return'] > 0:
            profitable_count += 1
            print(f"{i+1:2d}. {result['pair']:15} | Return: {result['total_return']*100:+.2f}% | Win Rate: {result['win_rate']:.1f}% | Trades: {result['trades']}")
    
    print(f"\n📈 Summary:")
    print(f"   Total Pairs Tested: {len(pairs_to_test)}")
    print(f"   Pairs with Enough Trades: {len(results)}")
    print(f"   Profitable Pairs: {profitable_count}")
    if len(results) > 0:
        print(f"   Success Rate: {profitable_count/len(results)*100:.1f}%")
    
    # Рекомендации для мониторинга
    if profitable_count > 0:
        print(f"\n💡 Recommended pairs for monitoring:")
        for result in results[:5]:
            if result['total_return'] > 0:
                print(f"   {result['pair']} (+{result['total_return']*100:.1f}%)")

def main():
    parser = argparse.ArgumentParser(description='Backtest pairs like in R')
    parser.add_argument('--pair', type=str, help='Test single pair (e.g., BTC_ETH)')
    parser.add_argument('--all', action='store_true', help='Test TOP 20 pairs automatically')
    parser.add_argument('--days', type=int, default=180, help='Days of historical data')
    parser.add_argument('--noadf', action='store_true', help='Disable ADF test')
    parser.add_argument('--limit', type=int, default=20, help='Limit number of pairs to test (default: 20)')
    
    args = parser.parse_args()
    
    if args.all:
        run_all_backtests(days=args.days, adf_test=not args.noadf, limit=args.limit)
    elif args.pair:
        # Запуск для одной пары
        analyzer = PairAnalyzer()
        target_pair = None
        for pair in analyzer.pairs:
            if pair['name'] == args.pair:
                target_pair = pair
                break
        
        if target_pair:
            result = run_single_backtest(args.pair, target_pair, args.days, not args.noadf)
            if result:
                print(f"\n🎯 RESULT for {args.pair}:")
                print(f"   Total Return: {result['total_return']*100:+.2f}%")
                print(f"   Win Rate: {result['win_rate']:.1f}%")
                print(f"   Trades: {result['trades']}")
        else:
            print(f"❌ Pair {args.pair} not found")
    else:
        print("❌ Specify --pair <name> or --all to test top 20 pairs")

if __name__ == "__main__":
    main()
