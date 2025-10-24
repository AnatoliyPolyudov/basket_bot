# backtester.py - Простой бэктестинг как в R
import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse
from pairs_core import PairAnalyzer

def fetch_historical_data(symbol: str, days: int = 365) -> pd.Series:
    """Загрузка исторических данных с OKX"""
    exchange = ccxt.okx({"enableRateLimit": True})
    
    since = exchange.parse8601((datetime.now() - timedelta(days=days)).isoformat())
    ohlcv = exchange.fetch_ohlcv(symbol, '1d', since=since)
    
    dates = [pd.Timestamp(x[0], unit='ms') for x in ohlcv]
    closes = [x[4] for x in ohlcv]
    
    return pd.Series(closes, index=dates, name=symbol)

def run_backtest(pair_name: str, days: int = 365):
    """Запуск бэктеста для одной пары"""
    print(f"🔍 Backtesting {pair_name} for {days} days...")
    
    # Находим пару в нашем списке
    analyzer = PairAnalyzer()
    target_pair = None
    for pair in analyzer.pairs:
        if pair['name'] == pair_name:
            target_pair = pair
            break
    
    if not target_pair:
        print(f"❌ Pair {pair_name} not found")
        return
    
    # Загружаем исторические данные
    print(f"📥 Loading historical data for {target_pair['asset_a']} and {target_pair['asset_b']}...")
    prices_a = fetch_historical_data(target_pair['asset_a'], days)
    prices_b = fetch_historical_data(target_pair['asset_b'], days)
    
    # Выравниваем данные по датам
    aligned_data = pd.DataFrame({
        'price_a': prices_a,
        'price_b': prices_b
    }).dropna()
    
    if len(aligned_data) < 60:
        print("❌ Not enough historical data")
        return
    
    # Рассчитываем спред
    aligned_data['spread'] = aligned_data['price_a'] / aligned_data['price_b']
    
    print(f"✅ Loaded {len(aligned_data)} days of data")
    
    # Бэктестинг (упрощенный)
    returns = []
    positions = []  # 1 = long, -1 = short, 0 = flat
    
    for i in range(35, len(aligned_data)):
        window_data = aligned_data['spread'].iloc[i-35:i]
        current_spread = aligned_data['spread'].iloc[i]
        
        # Z-score (как в R)
        z_score = (current_spread - window_data.mean()) / window_data.std()
        
        # Сигналы (как в R)
        if len(positions) == 0:
            if z_score > 1.0:
                positions.append(-1)  # Short
            elif z_score < -1.0:
                positions.append(1)   # Long
            else:
                positions.append(0)
        else:
            prev_pos = positions[-1]
            if abs(z_score) < 0.5:
                positions.append(0)   # Close
            else:
                positions.append(prev_pos)  # Hold
        
        # Расчет доходности (упрощенный)
        if i > 0:
            if positions[-1] == 1:  # Long A / Short B
                ret = (aligned_data['price_a'].iloc[i] / aligned_data['price_a'].iloc[i-1] - 1) - \
                      (aligned_data['price_b'].iloc[i] / aligned_data['price_b'].iloc[i-1] - 1)
            elif positions[-1] == -1:  # Short A / Long B
                ret = (aligned_data['price_b'].iloc[i] / aligned_data['price_b'].iloc[i-1] - 1) - \
                      (aligned_data['price_a'].iloc[i] / aligned_data['price_a'].iloc[i-1] - 1)
            else:
                ret = 0
            returns.append(ret)
    
    # Статистика (как в R)
    if returns:
        returns_series = pd.Series(returns)
        
        print("\n📊 BACKTEST RESULTS:")
        print(f"Period: {len(returns)} days")
        print(f"Total Return: {returns_series.sum()*100:.2f}%")
        print(f"Annual Return: {returns_series.mean()*252*100:.2f}%")
        print(f"Sharpe Ratio: {returns_series.mean()/returns_series.std()*np.sqrt(252):.2f}")
        print(f"Max Drawdown: {((returns_series + 1).cumprod() / (returns_series + 1).cumprod().cummax() - 1).min()*100:.2f}%")
        print(f"Win Rate: {(returns_series > 0).mean()*100:.1f}%")
        print(f"Total Trades: {len([i for i in range(1, len(positions)) if positions[i] != positions[i-1]])}")
    else:
        print("❌ No trades generated")

def main():
    parser = argparse.ArgumentParser(description='Backtest pairs like in R')
    parser.add_argument('--pair', type=str, required=True, help='Pair name (e.g., BTC_ETH)')
    parser.add_argument('--days', type=int, default=365, help='Days of historical data')
    
    args = parser.parse_args()
    
    run_backtest(args.pair, args.days)

if __name__ == "__main__":
    main()
