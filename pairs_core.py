import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller

def calculate_spread(df):
    # df: колонки ['A', 'B']
    X = sm.add_constant(df['B'])
    model = sm.OLS(df['A'], X).fit()
    beta = model.params[1]
    df['spread'] = df['A'] - beta * df['B']
    return df, beta

def test_stationarity(spread, significance=0.05):
    """Проверяет, стационарен ли спред через ADF тест"""
    result = adfuller(spread)
    pvalue = result[1]
    return pvalue < significance

def generate_signals(df, window=35, entry_z=1, exit_z=0.5):
    df['mean'] = df['spread'].rolling(window).mean()
    df['std'] = df['spread'].rolling(window).std()
    df['zscore'] = (df['spread'] - df['mean']) / df['std']
    
    df['signal'] = 0
    df.loc[df['zscore'] > entry_z, 'signal'] = -1  # short spread
    df.loc[df['zscore'] < -entry_z, 'signal'] = 1  # long spread
    df.loc[df['zscore'].abs() < exit_z, 'signal'] = 0  # close
    
    return df

def BacktestPair(df, window=35, adf_threshold=0.05):
    df, beta = calculate_spread(df)
    
    # Проверяем стационарность спреда
    if not test_stationarity(df['spread'], significance=adf_threshold):
        print("Спред не стационарен! Пара пропущена.")
        df['TotalReturn'] = 0
        return df
    
    df = generate_signals(df, window)
    df['TotalReturn'] = df['signal'].shift(1) * (df['spread'].diff())
    return df
