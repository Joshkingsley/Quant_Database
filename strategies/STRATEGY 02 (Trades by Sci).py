import os, sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


from scripts.fetch_data.fetch_duka import fetch_data
from scripts.fetch_data.form_candles import form_candles

from scripts.structure_lib.swing_detection import find_swing_points
from scripts.structure_lib.breakout_detection import classify_sweeps_and_breakouts
from scripts.structure_lib.classify_corrections import classify_corrections

import plotly.graph_objects as go

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

start_date = datetime(2026, 1, 1, 0, 0, 0) 
end_date = start_date + timedelta(weeks = 52)


try:
    with open('HTF_DATA.csv', 'r') as h_file:
        htf_data = pd.read_csv(h_file)
        print("\n Higher TimeFrame data read successfully")
    
    with open('LTF_DATA.csv', 'r') as l_file:
        ltf_data = pd.read_csv(l_file)
        print("\n Lower TimeFrame data read successfully\n")
        
    print("=" * 70)
    print(F"DATA FETCHED SUCCESSFULLY\n\nINSTRUMENT: XAU-USD\nSTART DATE: {start_date}\nEND DATE: {end_date}\nCURRENT TESTING STRATEGY: Trades By Sai (Youtube)")
    print("=" * 70, "\n\n")

except:
    print("\n", "=" * 70)
    print("Either HTF.csv or LTF.csv data does not exist. Proceeding with data fetch from client: DukaScopy")
    print("=" * 70)


    bid_h1, ask_h1, bid_m5, ask_m5 =  fetch_data(start_date, end_date)

    htf_data = form_candles(bid_h1, ask_h1)
    ltf_data = form_candles(bid_m5, ask_m5)

    try:
        htf_data.to_csv('HTF_DATA.csv')
        print("\n HTF.csv has been written and saved successfully")
    except:
        print("\nFailed to write to HTF.csv")

    
    try:
        ltf_data.to_csv('LTF_DATA.csv')
        print("\n LTF.csv has been written and saved successfully")
    except:
        print("\nFailed to write to LTF.csv")

df = find_swing_points(ltf_data, n = 6) 

df = classify_sweeps_and_breakouts(df)

df = classify_corrections(df)

def plot_breakouts(df, n=30, count=5, direction=None, start=0):
    """
    n         : candles shown before AND after each breakout
    count     : how many breakouts to plot
    direction : 'up', 'down', or None (both)
    start     : skip the first `start` breakouts (to page through them)
    """
    d = df.reset_index()
    tcol = d.columns[0]  # index/time column after reset
    for c in ('time', 'timestamp', 'datetime', 'date'):
        if c in d.columns:
            tcol = c
            break

    up = d['upside_breakout'].fillna(False).astype(bool)
    dn = d['downside_breakout'].fillna(False).astype(bool)

    # first bar of each breakout run only
    events = []
    if direction in (None, 'up'):
        events += [(i, 'up') for i in d.index[up & ~up.shift(1, fill_value=False)]]
    if direction in (None, 'down'):
        events += [(i, 'down') for i in d.index[dn & ~dn.shift(1, fill_value=False)]]
    events = sorted(events)[start:start + count]

    for i, side in events:
        lo, hi = max(0, i - n), min(len(d) - 1, i + n)
        w = d.iloc[lo:hi + 1]
        x = w[tcol].astype(str)

        fig = go.Figure(go.Candlestick(
            x=x, open=w['open'], high=w['high'], low=w['low'], close=w['close'],
            name='price'))

        # zone active at the breakout bar, drawn from breakout to window end
        zt, zb = d.at[i, 'active_resistance'], d.at[i, 'active_support']
        if zt == zt and zb == zb:
            fig.add_shape(type='rect', xref='x', yref='y',
                          x0=str(d.at[i, tcol]), x1=x.iloc[-1], y0=zb, y1=zt,
                          fillcolor='rgba(100,100,255,0.15)', line_width=0)
            fig.add_hline(y=zt, line_dash='dot', line_width=1)
            fig.add_hline(y=zb, line_dash='dot', line_width=1)

        # breakout marker
        fig.add_trace(go.Scatter(
            x=[str(d.at[i, tcol])],
            y=[d.at[i, 'high'] * 1.0003 if side == 'up' else d.at[i, 'low'] * 0.9997],
            mode='markers',
            marker=dict(symbol='triangle-up' if side == 'up' else 'triangle-down',
                        size=14, color='green' if side == 'up' else 'red'),
            name=f'{side} breakout'))

        fig.update_layout(title=f'{side.upper()} breakout @ {d.at[i, tcol]}  (idx {i}, ±{n} bars)',
                          xaxis_rangeslider_visible=False, xaxis_type='category',
                          height=600)
        fig.update_xaxes(nticks=12)
        fig.show()

def run_backtest_and_evaluate(df, initial_capital=10000.0, risk_pct=100, reward_ratio=3.0,
                                sl_buffer=0.0005, max_wait_bars=20):
    df = df.copy()
    risk = risk_pct / 100.0 if risk_pct > 1.0 else risk_pct

    capital = float(initial_capital)
    position = 0
    entry_price = stop_loss = take_profit = 0.0
    entry_idx = 0
    trade_risk_amount = 0.0
    pending = None

    df['trade_action'] = 'FLAT'
    df['pnl'] = 0.0
    df['equity'] = float(initial_capital)

    trades = []

    for i in range(len(df)):
        current_low = df['low'].iloc[i]
        current_high = df['high'].iloc[i]
        current_close = df['close'].iloc[i]

        # --- 1. MANAGE ACTIVE POSITIONS ---
        if position == 1:
            if current_low <= stop_loss:
                loss = -trade_risk_amount
                capital += loss
                df.iloc[i, df.columns.get_loc('trade_action')] = 'EXIT_SL'
                df.iloc[i, df.columns.get_loc('pnl')] = loss
                trades.append({'type': 'LONG', 'pnl': loss, 'duration': i - entry_idx,
                                'exit_reason': 'SL', 'r_multiple': -1.0})
                position = 0
            elif current_high >= take_profit:
                profit = trade_risk_amount * reward_ratio
                capital += profit
                df.iloc[i, df.columns.get_loc('trade_action')] = 'EXIT_TP'
                df.iloc[i, df.columns.get_loc('pnl')] = profit
                trades.append({'type': 'LONG', 'pnl': profit, 'duration': i - entry_idx,
                                'exit_reason': 'TP', 'r_multiple': reward_ratio})
                position = 0

        elif position == -1:
            if current_high >= stop_loss:
                loss = -trade_risk_amount
                capital += loss
                df.iloc[i, df.columns.get_loc('trade_action')] = 'EXIT_SL'
                df.iloc[i, df.columns.get_loc('pnl')] = loss
                trades.append({'type': 'SHORT', 'pnl': loss, 'duration': i - entry_idx,
                                'exit_reason': 'SL', 'r_multiple': -1.0})
                position = 0
            elif current_low <= take_profit:
                profit = trade_risk_amount * reward_ratio
                capital += profit
                df.iloc[i, df.columns.get_loc('trade_action')] = 'EXIT_TP'
                df.iloc[i, df.columns.get_loc('pnl')] = profit
                trades.append({'type': 'SHORT', 'pnl': profit, 'duration': i - entry_idx,
                                'exit_reason': 'TP', 'r_multiple': reward_ratio})
                position = 0

        # --- 2. ARM / RETEST / TRIGGER ---
        if position == 0:
            zone_top = df['active_resistance'].iloc[i]
            zone_bottom = df['active_support'].iloc[i]

            if df['upside_breakout'].iloc[i] and pd.notna(zone_top) and pd.notna(zone_bottom):
                if pending is None or pending['dir'] != 1:
                    pending = {'dir': 1, 'zone_top': zone_top, 'zone_bottom': zone_bottom, 'armed_idx': i}
            elif df['downside_breakout'].iloc[i] and pd.notna(zone_top) and pd.notna(zone_bottom):
                if pending is None or pending['dir'] != -1:
                    pending = {'dir': -1, 'zone_top': zone_top, 'zone_bottom': zone_bottom, 'armed_idx': i}

            if pending is not None:
                if i - pending['armed_idx'] > max_wait_bars:
                    pending = None
                elif pending['dir'] == 1:
                    if current_close < pending['zone_bottom']:
                        pending = None
                    elif current_low <= pending['zone_top']:
                        entry_price = pending['zone_top']
                        stop_loss = pending['zone_bottom'] * (1 - sl_buffer)
                        r_dist = entry_price - stop_loss
                        if r_dist > 0:
                            position = 1
                            take_profit = entry_price + r_dist * reward_ratio
                            entry_idx = i
                            trade_risk_amount = capital * risk
                            df.iloc[i, df.columns.get_loc('trade_action')] = 'BUY'
                        pending = None
                elif pending['dir'] == -1:
                    if current_close > pending['zone_top']:
                        pending = None
                    elif current_high >= pending['zone_bottom']:
                        entry_price = pending['zone_bottom']
                        stop_loss = pending['zone_top'] * (1 + sl_buffer)
                        r_dist = stop_loss - entry_price
                        if r_dist > 0:
                            position = -1
                            take_profit = entry_price - r_dist * reward_ratio
                            entry_idx = i
                            trade_risk_amount = capital * risk
                            df.iloc[i, df.columns.get_loc('trade_action')] = 'SELL'
                        pending = None

        df.iloc[i, df.columns.get_loc('equity')] = capital

    # --- 3. PERFORMANCE EVALUATION ---
    df['peak_equity'] = df['equity'].cummax()
    df['drawdown'] = (df['equity'] - df['peak_equity']) / df['peak_equity']
    max_dd_pct = df['drawdown'].min() * 100

    total_return_pct = ((df['equity'].iloc[-1] - initial_capital) / initial_capital) * 100
    total_net_profit = df['equity'].iloc[-1] - initial_capital

    total_trades = len(trades)
    winning_trades = [t for t in trades if t['pnl'] > 0]
    losing_trades = [t for t in trades if t['pnl'] < 0]
    win_rate = (len(winning_trades) / total_trades) * 100 if total_trades > 0 else 0

    gross_profit = sum(t['pnl'] for t in winning_trades)
    gross_loss = abs(sum(t['pnl'] for t in losing_trades))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (np.inf if gross_profit > 0 else 0)

    avg_r = np.mean([t['r_multiple'] for t in trades]) if trades else 0.0
    avg_win = gross_profit / len(winning_trades) if winning_trades else 0.0
    avg_loss = gross_loss / len(losing_trades) if losing_trades else 0.0
    expectancy = (win_rate / 100 * avg_win) - ((1 - win_rate / 100) * avg_loss)

    win_streaks, loss_streaks = [], []
    curr_win_streak, curr_loss_streak = 0, 0
    for t in trades:
        if t['pnl'] > 0:
            curr_win_streak += 1
            if curr_loss_streak > 0:
                loss_streaks.append(curr_loss_streak); curr_loss_streak = 0
        elif t['pnl'] < 0:
            curr_loss_streak += 1
            if curr_win_streak > 0:
                win_streaks.append(curr_win_streak); curr_win_streak = 0
    if curr_win_streak > 0: win_streaks.append(curr_win_streak)
    if curr_loss_streak > 0: loss_streaks.append(curr_loss_streak)

    max_win_streak = max(win_streaks) if win_streaks else 0
    min_win_streak = min(win_streaks) if win_streaks else 0
    avg_win_streak = np.mean(win_streaks) if win_streaks else 0.0
    max_loss_streak = max(loss_streaks) if loss_streaks else 0
    min_loss_streak = min(loss_streaks) if loss_streaks else 0
    avg_loss_streak = np.mean(loss_streaks) if loss_streaks else 0.0

    all_durations = [t['duration'] for t in trades]
    tp_durations = [t['duration'] for t in trades if t['exit_reason'] == 'TP']
    sl_durations = [t['duration'] for t in trades if t['exit_reason'] == 'SL']

    def get_duration_stats(dur_list):
        return (max(dur_list), min(dur_list), np.mean(dur_list)) if dur_list else (0, 0, 0.0)

    max_dur, min_dur, avg_dur = get_duration_stats(all_durations)
    max_tp_dur, min_tp_dur, avg_tp_dur = get_duration_stats(tp_durations)
    max_sl_dur, min_sl_dur, avg_sl_dur = get_duration_stats(sl_durations)

    print("\n" + "=" * 60)
    print("           STRATEGY PERFORMANCE REPORT          ")
    print("=" * 60)
    print(f"Initial Capital      : ${initial_capital:,.2f}")
    print(f"Final Equity         : ${df['equity'].iloc[-1]:,.2f}")
    print(f"Total Net Profit     : ${total_net_profit:,.2f}")
    print(f"Total Return         : {total_return_pct:.2f}%")
    print(f"Max Drawdown         : {max_dd_pct:.2f}%")
    print("-" * 60)
    print(f"Total Trades         : {total_trades}")
    print(f"Winning Trades       : {len(winning_trades)}")
    print(f"Losing Trades        : {len(losing_trades)}")
    print(f"Win Rate             : {win_rate:.2f}%")
    print(f"Profit Factor        : {profit_factor:.2f}")
    print(f"Avg R / Trade        : {avg_r:.2f}")
    print(f"Expectancy ($/trade) : ${expectancy:,.2f}")
    print("-" * 60)
    print("STREAK METRICS (Trades)")
    print(f"Win Streaks          : Max = {max_win_streak} | Min = {min_win_streak} | Avg = {avg_win_streak:.2f}")
    print(f"Loss Streaks         : Max = {max_loss_streak} | Min = {min_loss_streak} | Avg = {avg_loss_streak:.2f}")
    print("-" * 60)
    print("DURATION METRICS (Candles / Bars)")
    print(f"Overall Duration     : Max = {max_dur} | Min = {min_dur} | Avg = {avg_dur:.2f}")
    print(f"Take-Profit Duration : Max = {max_tp_dur} | Min = {min_tp_dur} | Avg = {avg_tp_dur:.2f}")
    print(f"Stop-Loss Duration   : Max = {max_sl_dur} | Min = {min_sl_dur} | Avg = {avg_sl_dur:.2f}")
    print("=" * 60 + "\n")

    return df

print(df.head(10))
print("\n", df.columns)

run_backtest_and_evaluate(df, initial_capital=10000, risk_pct=0.02, reward_ratio=3.0)
"""plot_breakouts(df, n=100, count=5)                  # first 5, both directions
plot_breakouts(df, n=100, count=3)  # wider window, longs only
plot_breakouts(df, n=100, count=5, start=5)         # next 5"""