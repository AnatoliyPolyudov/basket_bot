# backtester.py - С ADF ПРОВЕРКОЙ КАК В R
import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse
from pairs_core import PairAnalyzer
from statsmodels.tsa.stattools import adfuller

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

def is_pair_cointegrated(spread_data, critical_value=-2.58):
    """ADF тест как в R - тройная проверка на 120, 90, 60 дней"""
    if len(spread_data) < 120:
        return False
        
    try:
        # 120-дневный тест (как в R: i-120 до end)
        adf_120 = adfuller(spread_data[-120:], maxlag=1, regression='c', autolag=None)[0]
        if adf_120 > critical_value:
            return False
            
        # 90-дневный тест (как в R: i-90 до end)  
        adf_90 = adfuller(spread_data[-90:], maxlag=1, regression='c', autolag=None)[0]
        if adf_90 > critical_value:
            return False
            
        # 60-дневный тест (как в R: i-60 до end)
        adf_60 = adfuller(spread_data[-60:], maxlag=1, regression='c', autolag=None)[0]
        if adf_60 > critical_value:
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ ADF test error: {e}")
        return False

def run_backtest(pair_name: str, days: int = 365, adf_test: bool = True):
    """Запуск бэктеста с ADF проверкой как в R"""
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
    
    if len(aligned_data) < 130:  # Нужно минимум 130 дней для ADF теста
        print(f"❌ Need at least 130 days for ADF test, got {len(aligned_data)}")
        return
    
    aligned_data['spread'] = aligned_data['price_a'] / aligned_data['price_b']
    
    # ПАРАМЕТРЫ КАК В R
    entry_z = 1.0
    exit_z = 0.5
    stop_loss = 0.10
    max_hold_days = 30
    commission = 0.002
    critical_value = -2.58  # Как в R (10% уровень)
    
    print(f"🎯 Trading with ADF Filter (like in R):")
    print(f"   ADF Test: {'ON' if adf_test else 'OFF'}")
    print(f"   Critical Value: {critical_value}")
    print(f"   Entry Z: {entry_z}, Exit Z: {exit_z}")
    
    # Бэктестинг с ADF фильтром
    returns = []
    positions = []
    entry_prices = {}
    cointegrated_days = 0
    total_days = 0
    
    for i in range(130, len(aligned_data)):  # Начинаем с 130 дня как в R
        window = aligned_data['spread'].iloc[i-35:i]  # 35-дневное окно для Z-score
        current_spread = aligned_data['spread'].iloc[i]
        
        if window.std() > 0:
            z_score = (current_spread - window.mean()) / window.std()
        else:
            z_score = 0
        
        # ADF ПРОВЕРКА КАК В R ПРОЕКТЕ
        can_trade = True
        if adf_test:
            # Берем историю спреда для ADF теста (как в R)
            spread_history = aligned_data['spread'].iloc[:i+1]  # От начала до текущего дня
            
            # Тройной ADF тест на 120, 90, 60 дней
            can_trade = is_pair_cointegrated(spread_history, critical_value)
        
        total_days += 1
        if can_trade:
            cointegrated_days += 1
        
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
            
            print(f"🛑 {force_exit_reason} at day {i}")
            print(f"   Spread: {entry_spread:.4f} → {exit_spread:.4f}")
            print(f"   PnL: {pnl*100:+.2f}%")
            
            del entry_prices[current_position]
            positions.append(0)
            
        elif current_position == 0 and can_trade:  # Нет позиции И ADF пройден
            if z_score > entry_z:
                positions.append(-1)
                entry_prices[-1] = (current_spread, i)
                print(f"📈 ENTRY SHORT at day {i}: Z = {z_score:.2f}, Spread = {current_spread:.4f}")
            elif z_score < -entry_z:
                positions.append(1)
                entry_prices[1] = (current_spread, i)
                print(f"📈 ENTRY LONG at day {i}: Z = {z_score:.2f}, Spread = {current_spread:.4f}")
            else:
                positions.append(0)
                
        elif current_position == 1 and can_trade:  # Long позиция И ADF пройден
            if z_score > -exit_z:
                entry_spread, entry_idx = entry_prices[1]
                exit_spread = current_spread
                
                pnl = (exit_spread - entry_spread) / entry_spread
                pnl -= commission
                
                returns.append(pnl)
                print(f"📉 EXIT LONG at day {i}: Z = {z_score:.2f}")
                print(f"   Spread: {entry_spread:.4f} → {exit_spread:.4f}")
                print(f"   PnL: {pnl*100:+.2f}%")
                
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
                print(f"📉 EXIT SHORT at day {i}: Z = {z_score:.2f}")
                print(f"   Spread: {entry_spread:.4f} → {exit_spread:.4f}")
                print(f"   PnL: {pnl*100:+.2f}%")
                
                del entry_prices[-1]
                positions.append(0)
            else:
                positions.append(-1)
        else:
            # Не торгуем - ADF не пройден или нет позиции
            positions.append(current_position)
    
    # Результаты
    print(f"\n📊 ADF Statistics:")
    print(f"   Cointegrated Days: {cointegrated_days}/{total_days} ({cointegrated_days/total_days*100:.1f}%)")
    
    if returns:
        returns_series = pd.Series(returns)
        total_return = (returns_series + 1).prod() - 1
        
        print(f"\n🎯 BACKTEST RESULTS with ADF FILTER:")
        print(f"Total Return: {total_return*100:+.2f}%")
        print(f"Number of Trades: {len(returns)}")
        print(f"Win Rate: {(returns_series > 0).mean()*100:.1f}%")
        print(f"Avg Trade Return: {returns_series.mean()*100:+.2f}%")
        print(f"Best Trade: {returns_series.max()*100:+.2f}%")
        print(f"Worst Trade: {returns_series.min()*100:+.2f}%")
        
        if returns_series.std() > 0:
            sharpe = returns_series.mean() / returns_series.std() * np.sqrt(252)
            print(f"Sharpe Ratio: {sharpe:.2f}")
        
        equity_curve = (returns_series + 1).cumprod()
        max_drawdown = (equity_curve / equity_curve.cummax() - 1).min() * 100
        print(f"Max Drawdown: {max_drawdown:.2f}%")
        
    else:
        print(f"\n❌ No trades executed")
        if adf_test:
            print(f"   Pair may not be cointegrated enough for trading")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pair', type=str, required=True)
    parser.add_argument('--days', type=int, default=180)
    parser.add_argument('--noadf', action='store_true', help='Disable ADF test (like adfTest=FALSE in R)')
    
    args = parser.parse_args()
    run_backtest(args.pair, args.days, adf_test=not args.noadf)

if __name__ == "__main__":
    main()
