from pairs_core import BacktestPair
from backtester import BacktestPortfolio
import ccxt
from itertools import combinations

def get_top10_symbols():
    exchange = ccxt.okx()
    exchange.load_markets()
    # фильтрируем только спот пары USDT
    symbols = [s for s in exchange.symbols if '/USDT' in s]
    # сортируем по объёму 24h
    symbols = sorted(symbols, key=lambda x: exchange.fetch_ticker(x)['quoteVolume'], reverse=True)
    return symbols[:10]

def main():
    top10 = get_top10_symbols()
    pairs = list(combinations(top10, 2))
    
    print("Top-10 монет:", top10)
    print("Всего пар:", len(pairs))
    
    # Загружаем исторические данные и запускаем бэктест
    results = []
    for base, quote in pairs:
        print(f"Бэктест для пары {base}/{quote}")
        # fetch OHLCV для пары
        # Здесь можно добавить функцию загрузки CSV или fetch_ohlcv
        # df = load_data_from_csv_or_api(base, quote)
        # df_backtest = BacktestPair(df)
        # results.append(df_backtest['TotalReturn'])
    
    # Сборка портфеля
    # portfolio_returns = BacktestPortfolio(results)
    # print(portfolio_returns)

if __name__ == "__main__":
    main()
