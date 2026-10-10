import pandas as pd
import numpy as np

def form_candles(bid_df, ask_df):

    df = pd.DataFrame(index = bid_df.index)

    try:    
        df['open'] = (bid_df['open'] + ask_df['open']) / 2
        df['high'] = np.maximum(bid_df['high'], ask_df['high'])
        df['low'] = np.minimum(bid_df['low'], ask_df['low'])
        df['close'] = (bid_df['close'] + ask_df['close']) / 2

    except:    
        print("=" * 70)
        print("CANDLE FORMATION FAILED")
        print("=" * 70, "\n\n")
        return
    
    print("=" * 70)
    print("CANDLES FORMED SUCCESSFULLY")
    print("=" * 70, "\n\n")

    return df