# backtester.py - ИСПРАВЛЕННЫЙ РАСЧЕТ PnL
import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse
from pairs_core import PairAnalyzer

def fetch_historical_data(symbol: str, days: int = 365) -> pd.Series:
    """Загрузка исторических данных с OKX"""
    try:
        exchange = ccxt.okx({"enableRateLimit": True})
        ohlcv = exchange.fetch_ohlcv(symbol, '1d', limit=min(days, 365))
        
        dates = [pd.Timestamp(x[0], unit='ms') for x in ohlcv]
        closes = [x[4] for x in ohlcv]
        
        print(f"📊 Loaded {len(closes)} bars for {symbol}")
        return pd.Series(closes, index=dates, name=symbol)
        
    except Exception as e:
        print(f"❌ Error loading {symbol}: {e}")
        return pd.Series()

def run_backtest(pair_name: str, days: int = 365):
    """Запуск бэктеста с исправленной логикой PnL"""
    print(f"🔍 Backtesting {pair_name} for {days} days...")
    
    analyzer = PairAnalyzer()
    target_pair = None
    for pair in analyzer.pairs:
        if pair['name'] == pair_name:
            target_pair = pair
            break
    
    if not target_pair:
        print(f"❌ Pair {pair_name} not found")
        return
    
    # Загружаем данные
    prices_a = fetch_historical_data(target_pair['asset_a'], days)
    prices_b = fetch_historical_data(target_pair['asset_b'], days)
    
    if prices_a.empty or prices_b.empty:
        return
    
    aligned_data = pd.DataFrame({
        'price_a': prices_a,
        'price_b': prices_b
    }).dropna()
    
    print(f"✅ Aligned data: {len(aligned_data)} days")
    
    if len(aligned_data) < 60:
        return
    
    aligned_data['spread'] = aligned_data['price_a'] / aligned_data['price_b']
    
    # Бэктестинг с ПРАВИЛЬНЫМ расчетом PnL
    returns = []
    positions = []  # 1 = long A/short B, -1 = short A/long B, 0 = flat
    entry_z = 1.0
    exit_z = 0.5
    
    # Словарь для хранения цен входа
    entry_prices = {}  # {position_type: (entry_spread, entry_idx)}
    
    print(f"🎯 Trading logic: Enter when |Z| > {entry_z}, Exit when |Z| < {exit_z}")
    
    for i in range(35, len(aligned_data)):
        window = aligned_data['spread'].iloc[i-35:i]
        current_spread = aligned_data['spread'].iloc[i]
        
        if window.std() > 0:
            z_score = (current_spread - window.mean()) / window.std()
        else:
            z_score = 0
        
        # Текущая позиция
        current_position = positions[-1] if positions else 0
        
        # ЛОГИКА ТРЕЙДИНГА
        if current_position == 0:  # Нет позиции
            if z_score > entry_z:  # Spread высокий - short A / long B
                positions.append(-1)
                entry_prices[-1] = (current_spread, i)
                print(f"📈 ENTRY SHORT at day {i}: Z = {z_score:.2f}, Spread = {current_spread:.4f}")
            elif z_score < -entry_z:  # Spread низкий - long A / short B
                positions.append(1)
                entry_prices[1] = (current_spread, i)
                print(f"📈 ENTRY LONG at day {i}: Z = {z_score:.2f}, Spread = {current_spread:.4f}")
            else:
                positions.append(0)
                
        elif current_position == 1:  # Long A / Short B
            if z_score > -exit_z:  # Z-score вернулся к 0 - закрываем
                if 1 in entry_prices:
                    entry_spread, entry_idx = entry_prices[1]
                    exit_spread = current_spread
                    
                    # PnL для long A/short B: выигрываем если спред растет
                    pnl = (exit_spread - entry_spread) / entry_spread
                    pnl -= 0.002  # Комиссия
                    
                    returns.append(pnl)
                    print(f"📉 EXIT LONG at day {i}: Z = {z_score:.2f}")
                    print(f"   Spread: {entry_spread:.4f} → {exit_spread:.4f}")
                    print(f"   PnL: {pnl*100:+.2f}%")
                    
                    del entry_prices[1]
                
                positions.append(0)
            else:
                positions.append(1)  # Держим позицию
                
        elif current_position == -1:  # Short A / Long B
            if z_score < exit_z:  # Z-score вернулся к 0 - закрываем
                if -1 in entry_prices:
                    entry_spread, entry_idx = entry_prices[-1]
                    exit_spread = current_spread
                    
                    # PnL для short A/long B: выигрываем если спред падает
                    pnl = (entry_spread - exit_spread) / entry_spread
                    pnl -= 0.002  # Комиссия
                    
                    returns.append(pnl)
                    print(f"📉 EXIT SHORT at day {i}: Z = {z_score:.2f}")
                    print(f"   Spread: {entry_spread:.4f} → {exit_spread:.4f}")
                    print(f"   PnL: {pnl*100:+.2f}%")
                    
                    del entry_prices[-1]
                
                positions.append(0)
            else:
                positions.append(-1)  # Держим позицию
    
    # Результаты
    if returns:
        returns_series = pd.Series(returns)
        total_return = (returns_series + 1).prod() - 1
        
        print(f"\n🎯 BACKTEST RESULTS:")
        print(f"Total Return: {total_return*100:+.2f}%")
        print(f"Number of Trades: {len(returns)}")
        print(f"Win Rate: {(returns_series > 0).mean()*100:.1f}%")
        print(f"Avg Trade Return: {returns_series.mean()*100:+.2f}%")
        print(f"Best Trade: {returns_series.max()*100:+.2f}%")
        print(f"Worst Trade: {returns_series.min()*100:+.2f}%")
        
        # Дополнительная статистика
        if returns_series.std() > 0:
            sharpe = returns_series.mean() / returns_series.std() * np.sqrt(252)
            print(f"Sharpe Ratio: {sharpe:.2f}")
        
        # Покажем несколько сделок для проверки
        print(f"\n📋 Trade Details:")
        for j, ret in enumerate(returns):
            print(f"  Trade {j+1}: {ret*100:+.2f}%")
    else:
        print(f"\n❌ No trades executed")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pair', type=str, required=True)
    parser.add_argument('--days', type=int, default=180)
    
    args = parser.parse_args()
    run_backtest(args.pair, args.days)

if __name__ == "__main__":
    main()
