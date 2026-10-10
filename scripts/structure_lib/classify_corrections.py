def classify_corrections(df):
    df = df.copy()
    
    df['bullish_correction'] = (df['close'] < df['close'].shift(1)) & \
                               (df['low'] > df['active_support'])
                               
    df['bearish_correction'] = (df['close'] > df['close'].shift(1)) & \
                               (df['high'] < df['active_resistance'])
                               
    df['correction_zone'] = df['bullish_correction'] | df['bearish_correction']
    
    return df