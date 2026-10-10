import pandas as pd
import numpy as np

def classify_sweeps_and_breakouts(df):
    df = df.copy()
    
    df['active_resistance'] = df['swing_high_price'].ffill().shift(1)
    df['active_support'] = df['swing_low_price'].ffill().shift(1)
    
    distinct_highs = df['swing_high_price'].dropna()
    df['prev_resistance'] = distinct_highs.shift(1).reindex(df.index).ffill().shift(1)

    distinct_lows = df['swing_low_price'].dropna()
    df['prev_support'] = distinct_lows.shift(1).reindex(df.index).ffill().shift(1)
    
    df['upside_sweep'] = (df['high'] > df['active_resistance']) & (df['close'] < df['active_resistance'])
    df['downside_sweep'] = (df['low'] < df['active_support']) & (df['close'] > df['active_support'])
    
    df['upside_breakout'] = df['close'] > df['active_resistance']
    df['downside_breakout'] = df['close'] < df['active_support']
    
    df['breakout_zone'] = df['upside_breakout'] | df['downside_breakout']

    conditions = [df['upside_breakout'], df['downside_breakout']]
    
    choices_close = [df['close'], df['close']]
    df['breakout_price'] = np.select(conditions, choices_close, default=np.nan)
    
    choices_level = [df['active_resistance'], df['active_support']]
    df['breakout_level_price'] = np.select(conditions, choices_level, default=np.nan)
    
    df['last_breakout_price'] = df['breakout_price'].ffill()
    
    return df