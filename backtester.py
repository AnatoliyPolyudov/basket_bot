# backtester.py - С АДАПТИВНЫМИ ПОРОГАМИ
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
    """Запуск бэктеста с диагностикой"""
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
    
    # ДИАГНОСТИКА: Анализируем Z-score распределение
    z_scores = []
    for i in range(35, len(aligned_data)):
        window = aligned_data['spread'].iloc[i-35:i]
        current = aligned_data['spread'].iloc[i]
        if window.std() > 0:
            z = (current - window.mean()) / window.std()
            z_scores.append(z)
    
    if z_scores:
        z_scores_series = pd.Series(z_scores)
        print(f"📊 Z-score analysis:")
        print(f"   Min: {z_scores_series.min():.2f}")
        print(f"   Max: {z_scores_series.max():.2f}") 
        print(f"   Mean: {z_scores_series.mean():.2f}")
        print(f"   Std: {z_scores_series.std():.2f}")
        print(f"   |Z| > 1.0: {(np.abs(z_scores_series) > 1.0).mean()*100:.1f}% of time")
        
        # АДАПТИВНЫЕ ПОРОГИ на основе данных
        if z_scores_series.max() < 1.0:
            entry_z = z_scores_series.quantile(0.8)  # 80% перцентиль
            exit_z = z_scores_series.quantile(0.6)   # 60% перцентиль
            print(f"🎯 Using adaptive thresholds: Entry Z > {entry_z:.2f}, Exit Z < {exit_z:.2f}")
        else:
            entry_z = 1.0
            exit_z = 0.5
            print(f"🎯 Using standard thresholds: Entry Z > {entry_z:.2f}, Exit Z < {exit_z:.2f}")
    else:
        print("❌ No Z-scores calculated")
        return
    
    # Бэктестинг с правильной логикой
    returns = []
    positions = []
    in_position = False
    entry_price_ratio = 0
    
    for i in range(35, len(aligned_data)):
        window = aligned_data['spread'].iloc[i-35:i]
        current_spread = aligned_data['spread'].iloc[i]
        
        if window.std() > 0:
            z_score = (current_spread - window.mean()) / window.std()
        else:
            z_score = 0
        
        # ЛОГИКА ТРЕЙДИНГА (исправленная)
        if not in_position:
            if z_score > entry_z:  # Spread слишком высок - short A / long B
                positions.append(-1)
                in_position = True
                entry_price_ratio = aligned_data['price_a'].iloc[i] / aligned_data['price_b'].iloc[i]
            elif z_score < -entry_z:  # Spread слишком низок - long A / short B
                positions.append(1)
                in_position = True
                entry_price_ratio = aligned_data['price_a'].iloc[i] / aligned_data['price_b'].iloc[i]
            else:
                positions.append(0)
        else:
            current_pos = positions[-1]
            # Закрываем позицию когда Z-score возвращается к 0
            if current_pos == 1 and z_score > -exit_z:  # Был long, закрываем
                positions.append(0)
                in_position = False
            elif current_pos == -1 and z_score < exit_z:  # Был short, закрываем
                positions.append(0) 
                in_position = False
            else:
                positions.append(current_pos)
        
        # Расчет PnL
        if i > 0 and len(positions) > 1:
            if positions[-1] == 0 and positions[-2] != 0:  # Закрытие позиции
                exit_price_ratio = aligned_data['price_a'].iloc[i] / aligned_data['price_b'].iloc[i]
                
                if positions[-2] == 1:  # Был long A/short B
                    pnl = (exit_price_ratio - entry_price_ratio) / entry_price_ratio
                else:  # Был short A/long B  
                    pnl = (entry_price_ratio - exit_price_ratio) / entry_price_ratio
                
                # Комиссия
                pnl -= 0.002
                returns.append(pnl)
    
    # Результаты
    if returns:
        returns_series = pd.Series(returns)
        total_return = (returns_series + 1).prod() - 1
        
        print(f"\n🎯 BACKTEST RESULTS:")
        print(f"Total Return: {total_return*100:.2f}%")
        print(f"Number of Trades: {len(returns)}")
        print(f"Win Rate: {(returns_series > 0).mean()*100:.1f}%")
        print(f"Avg Trade Return: {returns_series.mean()*100:.2f}%")
    else:
        print(f"\n❌ No trades executed")
        print(f"Z-score range was: {min(z_scores):.2f} to {max(z_scores):.2f}")
        print(f"Try different pair or adjust thresholds")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pair', type=str, required=True)
    parser.add_argument('--days', type=int, default=180)
    
    args = parser.parse_args()
    run_backtest(args.pair, args.days)

if __name__ == "__main__":
    main()
