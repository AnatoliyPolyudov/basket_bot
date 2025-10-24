from pairs_core import BacktestPair
from backtester import BacktestPortfolio
import ccxt
from itertools import combinations
import pandas as pd

# --- Настройки ---
TIMEFRAME = '1d'
LIMIT = 365  # дней истории

def get_top10_symbols():
    exchange = ccxt.okx()
    exchange.load_markets()
    symbols = [s for s in exchange.symbols if '/USDT' in s]
    # сортируем по 24h объёму
    symbols = sorted(
        symbols, 
        key=lambda x: exchange.fetch_ticker(x)['quoteVolume'], 
        reverse=True
    )
    return symbols[:10]

def fetch_ohlcv_df(symbol):
    exchange = ccxt.okx()
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=LIMIT)
    df = pd.DataFrame(ohlcv, columns=['timestamp','open','high','low','close','volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df.rename(columns={'close': symbol}, inplace=True)
    return df[[symbol]]

def main():
    top10 = get_top10_symbols()
    pairs = list(combinations(top10, 2))
    
    print("Top-10 монет:", top10)
    print("Всего пар:", len(pairs))
    
    results = []
    for base, quote in pairs:
        print(f"Бэктест для пары {base}/{quote}")
        
        # Загружаем цены
        df_base = fetch_ohlcv_df(base)
        df_quote = fetch_ohlcv_df(quote)
        
        # Объединяем по дате
        df = df_base.join(df_quote, how='inner')
        df.dropna(inplace=True)
        
        # Бэктест пары
        df_backtest = BacktestPair(df)
        results.append(df_backtest['TotalReturn'])
    
    # Портфель
    portfolio_returns = BacktestPortfolio(results)
    print("Портфельная доходность:")
    print(portfolio_returns.tail())

if __name__ == "__main__":
    main()
