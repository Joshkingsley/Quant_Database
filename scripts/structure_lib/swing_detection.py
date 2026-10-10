import pandas as pd
import numpy as np

def find_swing_points(df, n=2):
    df = df.copy()

    is_swing_high = pd.Series(True, index=df.index)
    is_swing_low = pd.Series(True, index=df.index)

    for i in range(1, n + 1):
        is_swing_high &= (df['high'] > df['high'].shift(i)) & (df['high'] > df['high'].shift(-i))
        is_swing_low &= (df['low'] < df['low'].shift(i)) & (df['low'] < df['low'].shift(-i))

    df['swing_high'] = is_swing_high
    df['swing_low'] = is_swing_low

    df['swing_high_price'] = np.where(df['swing_high'], df['high'], np.nan)
    df['swing_low_price'] = np.where(df['swing_low'], df['low'], np.nan)

    return df