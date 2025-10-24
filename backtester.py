# backtester.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
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
        
        # OKX часто ограничивает историю, берем что есть
        timeframe = '1d'
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=min(days, 365))
        
        if not ohlcv:
            print(f"❌ No data for {symbol}")
            return pd.Series()
            
        dates = [pd.Timestamp(x[0], unit='ms') for x in ohlcv]
        closes = [x[4] for x in ohlcv]
        
        print(f"📊 Loaded {len(closes)} bars for {symbol}")
        return pd.Series(closes, index=dates, name=symbol)
        
    except Exception as e:
        print(f"❌ Error loading {symbol}: {e}")
        return pd.Series()

def run_backtest(pair_name: str, days: int = 365):
    """Запуск бэктеста для одной пары"""
    print(f"🔍 Backtesting {pair_name} for {days} days...")
    
    analyzer = PairAnalyzer()
    target_pair = None
    for pair in analyzer.pairs:
        if pair['name'] == pair_name:
            target_pair = pair
            break
    
    if not target_pair:
        print(f"❌ Pair {pair_name} not found. Available pairs:")
        for p in analyzer.pairs[:5]:  # Покажем первые 5
            print(f"  - {p['name']}")
        return
    
    # Загружаем исторические данные
    print(f"📥 Loading {target_pair['asset_a']} and {target_pair['asset_b']}...")
    prices_a = fetch_historical_data(target_pair['asset_a'], days)
    prices_b = fetch_historical_data(target_pair['asset_b'], days)
    
    if prices_a.empty or prices_b.empty:
        print("❌ Failed to load historical data")
        return
    
    # Выравниваем данные
    aligned_data = pd.DataFrame({
        'price_a': prices_a,
        'price_b': prices_b
    }).dropna()
    
    print(f"✅ Aligned data: {len(aligned_data)} days")
    
    if len(aligned_data) < 60:
        print(f"❌ Need at least 60 days, got {len(aligned_data)}")
        return
    
    # Рассчитываем спред
    aligned_data['spread'] = aligned_data['price_a'] / aligned_data['price_b']
    
    # Бэктестинг с исправленной логикой
    returns = []
    positions = []  # 1 = long A/short B, -1 = short A/long B, 0 = flat
    entry_z = 1.0   # Z-score для входа
    exit_z = 0.5    # Z-score для выхода
    
    for i in range(35, len(aligned_data)):
        window_data = aligned_data['spread'].iloc[i-35:i]
        current_spread = aligned_data['spread'].iloc[i]
        
        # Z-score
        mean = window_data.mean()
        std = window_data.std()
        
        if std == 0:  # Избегаем деления на 0
            z_score = 0
        else:
            z_score = (current_spread - mean) / std
        
        # Логика трейдинга (ИСПРАВЛЕННАЯ)
        if not positions:  # Нет открытой позиции
            if z_score > entry_z:
                positions.append(-1)  # Short A / Long B
            elif z_score < -entry_z:
                positions.append(1)   # Long A / Short B
            else:
                positions.append(0)
        else:
            current_pos = positions[-1]
            # Закрываем если Z-score вернулся к 0
            if current_pos == 1 and z_score > -exit_z:  # Был long, теперь закрываем
                positions.append(0)
            elif current_pos == -1 and z_score < exit_z:  # Был short, теперь закрываем
                positions.append(0)
            else:
                positions.append(current_pos)  # Держим позицию
        
        # Расчет доходности (ИСПРАВЛЕННЫЙ)
        if i > 0 and len(positions) > 1:
            current_pos = positions[-1]
            prev_pos = positions[-2]
            
            # Доходность только при изменении позиции или удержании
            if current_pos != 0 or prev_pos != 0:
                if current_pos == 1:  # Long A / Short B
                    ret_a = (aligned_data['price_a'].iloc[i] / aligned_data['price_a'].iloc[i-1] - 1)
                    ret_b = (aligned_data['price_b'].iloc[i] / aligned_data['price_b'].iloc[i-1] - 1)
                    ret = ret_a - ret_b
                elif current_pos == -1:  # Short A / Long B
                    ret_a = (aligned_data['price_a'].iloc[i] / aligned_data['price_a'].iloc[i-1] - 1)
                    ret_b = (aligned_data['price_b'].iloc[i] / aligned_data['price_b'].iloc[i-1] - 1)
                    ret = ret_b - ret_a
                else:
                    ret = 0
                
                # Добавляем комиссию при смене позиции
                if current_pos != prev_pos and prev_pos != 0:
                    ret -= 0.001  # 0.1% комиссия
                    
                returns.append(ret)
    
    # Статистика
    if returns and len(returns) > 10:
        returns_series = pd.Series(returns)
        total_return = (returns_series + 1).prod() - 1
        
        # Sharpe ratio с защитой от нулевой волатильности
        if returns_series.std() > 0:
            sharpe = returns_series.mean() / returns_series.std() * np.sqrt(252)
        else:
            sharpe = 0
            
        # Максимальная просадка
        equity_curve = (returns_series + 1).cumprod()
        drawdown = (equity_curve / equity_curve.cummax() - 1).min()
        
        print(f"\n🎯 BACKTEST RESULTS for {pair_name}:")
        print(f"Period: {len(returns)} trading days")
        print(f"Total Return: {total_return*100:.2f}%")
        print(f"Annual Return: {returns_series.mean()*252*100:.2f}%")
        print(f"Sharpe Ratio: {sharpe:.2f}")
        print(f"Max Drawdown: {drawdown*100:.2f}%")
        print(f"Win Rate: {(returns_series > 0).mean()*100:.1f}%")
        
        # Считаем сделки (смены позиций)
        trades = sum(1 for i in range(1, len(positions)) if positions[i] != positions[i-1])
        print(f"Total Trades: {trades}")
        
        # Покажем несколько Z-score для диагностики
        print(f"\n📊 Sample Z-scores (last 5 days):")
        for j in range(max(0, len(aligned_data)-5), len(aligned_data)):
            window = aligned_data['spread'].iloc[j-35:j]
            current = aligned_data['spread'].iloc[j]
            z = (current - window.mean()) / window.std() if window.std() > 0 else 0
            print(f"  Day {j}: Z = {z:.2f}, Position = {positions[j-35] if j-35 < len(positions) else 'N/A'}")
            
    else:
        print(f"\n❌ No valid trades generated for {pair_name}")
        print("Possible reasons:")
        print("  - Z-scores never crossed entry/exit thresholds")
        print("  - Not enough volatility in the pair")
        print("  - Try different parameters or another pair")

def main():
    parser = argparse.ArgumentParser(description='Backtest pairs like in R')
    parser.add_argument('--pair', type=str, required=True, help='Pair name (e.g., BTC_ETH)')
    parser.add_argument('--days', type=int, default=365, help='Days of historical data')
    
    args = parser.parse_args()
    
    run_backtest(args.pair, args.days)

if __name__ == "__main__":
    main()
