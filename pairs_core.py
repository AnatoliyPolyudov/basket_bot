import pandas as pd
import numpy as np
import statsmodels.api as sm

def calculate_spread(df):
    # df: колонки ['A', 'B']
    X = sm.add_constant(df['B'])
    model = sm.OLS(df['A'], X).fit()
    beta = model.params[1]
    df['spread'] = df['A'] - beta * df['B']
    return df, beta

def generate_signals(df, window=35, entry_z=1, exit_z=0.5):
    df['mean'] = df['spread'].rolling(window).mean()
    df['std'] = df['spread'].rolling(window).std()
    df['zscore'] = (df['spread'] - df['mean']) / df['std']
    
    df['signal'] = 0
    df.loc[df['zscore'] > entry_z, 'signal'] = -1  # short spread
    df.loc[df['zscore'] < -entry_z, 'signal'] = 1  # long spread
    df.loc[df['zscore'].abs() < exit_z, 'signal'] = 0  # close
    
    return df

def BacktestPair(df, window=35):
    df, beta = calculate_spread(df)
    df = generate_signals(df, window)
    # здесь можно добавить расчёт доходности на основе сигналов
    df['TotalReturn'] = df['signal'].shift(1) * (df['spread'].diff())
    return df
