import pandas as pd

def BacktestPortfolio(returns_list):
    # returns_list: список Series TotalReturn для каждой пары
    df = pd.concat(returns_list, axis=1)
    portfolio_return = df.mean(axis=1)
    return portfolio_return
