import os, re, time, html
from datetime import datetime
import numpy as np, pandas as pd, requests
import MetaTrader5 as mt5

# ---------- config ----------
SYMBOL, TF = "BTCUSD", mt5.TIMEFRAME_M1
SWING_N, BARS = 6, 3600
RISK_PCT, RR, SL_BUFFER, MAX_WAIT_BARS = 0.02, 3.0, 0.0005, 20
MAGIC, ALLOW_LIVE, HEARTBEAT_SEC = 90210, False, 30
TG_TOKEN, TG_CHAT = os.getenv("TELEGRAM_BOT_TOKEN", ""), os.getenv("TELEGRAM_CHAT_ID", "")

DIGITS = 2
pending = None      # {"ticket", "dir", "top", "bottom", "bars", "filled"}
traded = set()      # one trade per zone


# ---------- console log (everything) ----------
def log(tag, msg):
    print(f"{datetime.now():%H:%M:%S} [{tag:<6}] {msg}", flush=True)


def px(x):
    return f"{x:.{DIGITS}f}"


# ---------- telegram (important events only) ----------
def send_tg(text):
    if not (TG_TOKEN and TG_CHAT):
        return False
    try:
        r = requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", timeout=10,
                          json={"chat_id": TG_CHAT, "text": text, "parse_mode": "HTML",
                                "disable_web_page_preview": True})
        if not r.ok:
            log("TG", f"FAILED {r.status_code}: {r.text[:150]}")
        return r.ok
    except Exception as e:
        log("TG", f"FAILED: {e}")
        return False


def card(title, rows=()):
    """Bold title + aligned monospace rows."""
    body = "\n".join(f"{k:<6} {v}" for k, v in rows)
    return f"{title}\n<pre>{html.escape(body)}</pre>" if body else title


def tg(text):
    log("ALERT", re.sub(r"<[^>]+>", "", text).replace("\n", " | "))
    if not (TG_TOKEN and TG_CHAT):
        log("TG", "not configured (set TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID), alert not sent")
        return
    send_tg(text)

alerted = set()

def tg_once(key, text):
    if key in alerted:
        return
    alerted.add(key)
    tg(text)


# ---------- data ----------
def fetch_data(n=BARS):
    rates = mt5.copy_rates_from_pos(SYMBOL, TF, 1, n)      # pos=1 skips the forming candle
    if rates is None or len(rates) == 0:
        log("DATA", f"no rates returned: {mt5.last_error()}")
        return None
    return pd.DataFrame(rates)


def clean_ohlc(raw):
    n0 = len(raw)
    df = raw[["time", "open", "high", "low", "close"]].copy()
    df["time"] = pd.to_datetime(df["time"], unit="s")       # broker server time
    df = df.drop_duplicates("time").sort_values("time").dropna().set_index("time")
    df = df[df.high >= df.low]
    if len(df) != n0:
        log("DATA", f"cleaning dropped {n0 - len(df)} bad rows ({n0} -> {len(df)})")
    return df


# ---------- structure ----------
def detect_swings(df, n=SWING_N):
    hi = pd.Series(True, index=df.index)
    lo = hi.copy()
    for i in range(1, n + 1):
        hi &= (df.high > df.high.shift(i)) & (df.high > df.high.shift(-i))
        lo &= (df.low < df.low.shift(i)) & (df.low < df.low.shift(-i))
    df = df.copy()
    df["swing_high"], df["swing_low"] = df.high.where(hi), df.low.where(lo)
    return df


def detect_breakout(df):
    """Zone comes from candles BEFORE the latest one, so no look-ahead."""
    prior, last = df.iloc[:-1], df.iloc[-1]
    sw = detect_swings(prior)
    sh, sl_ = sw.swing_high.dropna(), sw.swing_low.dropna()
    if sh.empty or sl_.empty:
        log("ZONE", f"no zone yet (swing highs={len(sh)}, swing lows={len(sl_)})")
        tg_once(("nozone", len(sh), len(sl_)),
                card(f"⚪ <b>{SYMBOL}</b> · zone not tradable", [("Why", f"no swings yet (H={len(sh)} L={len(sl_)})")]))
        return None
    top, bottom = sh.iloc[-1], sl_.iloc[-1]
    log("ZONE", f"top={px(top)} (swing {sh.index[-1]:%H:%M}) | bottom={px(bottom)} (swing {sl_.index[-1]:%H:%M}) "
                f"| range={px(top - bottom)} | swings H={len(sh)} L={len(sl_)}")
    if top <= bottom:
        log("ZONE", "invalid (top <= bottom), ignored")
        tg_once(("inv", round(top, 5), round(bottom, 5)),
                card(f"⚪ <b>{SYMBOL}</b> · zone not tradable", [("Why", "top <= bottom"), ("Top", px(top)), ("Bottom", px(bottom))]))
        return None
    c = last.close
    if c > top:
        d = 1
        log("SIGNAL", f"close {px(c)} > top {px(top)} -> UPSIDE breakout")
    elif c < bottom:
        d = -1
        log("SIGNAL", f"close {px(c)} < bottom {px(bottom)} -> DOWNSIDE breakout")
    else:
        log("ZONE", f"close {px(c)} inside zone ({px(top - c)} below top, {px(c - bottom)} above bottom)")
        return None
    return {"dir": d, "top": top, "bottom": bottom, "time": df.index[-1]}


# ---------- trading ----------
def build_order(b):
    long = b["dir"] == 1
    entry = b["top"] if long else b["bottom"]                                    # retest of broken level
    sl = b["bottom"] * (1 - SL_BUFFER) if long else b["top"] * (1 + SL_BUFFER)   # opposite zone edge
    return entry, sl, entry + b["dir"] * abs(entry - sl) * RR


def lot_size(entry, sl, long):
    acc, info = mt5.account_info(), mt5.symbol_info(SYMBOL)
    loss = mt5.order_calc_profit(mt5.ORDER_TYPE_BUY if long else mt5.ORDER_TYPE_SELL,
                                 SYMBOL, 1.0, entry, sl)               # P/L of 1 lot hitting SL
    if not loss:
        log("LOTS", f"order_calc_profit failed: {mt5.last_error()}")
        return 0.0
    risk = acc.balance * RISK_PCT
    raw = risk / abs(loss)
    lots = min(np.floor(raw / info.volume_step + 1e-9) * info.volume_step, info.volume_max)
    log("LOTS", f"balance={acc.balance:,.2f} risk({RISK_PCT:.0%})={risk:,.2f} | loss/1lot={abs(loss):,.2f} "
                f"| raw={raw:.4f} -> {lots:.2f} (min={info.volume_min}, step={info.volume_step}, max={info.volume_max})")
    return round(lots, 2) if lots >= info.volume_min else 0.0          # never over-risk with min lot


def execute(b):
    global pending
    long = b["dir"] == 1
    info, tick = mt5.symbol_info(SYMBOL), mt5.symbol_info_tick(SYMBOL)
    entry, sl, tp = (round(x, info.digits) for x in build_order(b))
    gap = info.trade_stops_level * info.point
    price_ok = entry < tick.ask - gap if long else entry > tick.bid + gap
    side = "BUY LIMIT" if long else "SELL LIMIT"
    head = f"{'🟢' if long else '🔴'} <b>{SYMBOL}</b> · {side}"
    log("ORDER", f"plan {side} entry={px(entry)} sl={px(sl)} tp={px(tp)} | bid={px(tick.bid)} ask={px(tick.ask)} "
                 f"| min stop gap={px(gap)} | price_ok={price_ok}")
    lots = lot_size(entry, sl, long)
    delay = tick.time - (b["time"].timestamp() + 60)      # secs from breakout candle close to now

    if not price_ok or lots == 0:
        why = "price already past entry" if not price_ok else "min lot exceeds 2% risk"
        log("SKIP", f"{side} @ {px(entry)}: {why}")
        tg(card(f"⚠️ <b>{SYMBOL}</b> · {side} skipped", [("Entry", px(entry)), ("Why", why)]))
        return
    res = mt5.order_send({
        "action": mt5.TRADE_ACTION_PENDING, "symbol": SYMBOL, "volume": lots,
        "type": mt5.ORDER_TYPE_BUY_LIMIT if long else mt5.ORDER_TYPE_SELL_LIMIT,
        "price": entry, "sl": sl, "tp": tp, "magic": MAGIC,
        "comment": "zone-breakout", "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN})
    log("ORDER", f"order_send retcode={res.retcode} comment='{res.comment}' ticket={res.order}")
    if res.retcode != mt5.TRADE_RETCODE_DONE:
        tg(card(f"❌ <b>{SYMBOL}</b> · {side} rejected", [("Code", res.retcode), ("Info", res.comment)]))
        return
    pending = {"ticket": res.order, "dir": b["dir"], "top": b["top"], "bottom": b["bottom"],
               "bars": 0, "filled": False}
    log("PEND", f"tracking ticket {res.order} (waiting for retest, max {MAX_WAIT_BARS} candles)")
    risk_money = mt5.account_info().balance * RISK_PCT
    tg(card(head, [
        ("Entry", px(entry)),
        ("SL", f"{px(sl)}  ({px(abs(entry - sl))} away)"),
        ("TP", f"{px(tp)}  (1:{RR:g})"),
        ("Lots", f"{lots}  (risk ${risk_money:,.2f})"),
        ("Zone", f"{px(b['bottom'])} - {px(b['top'])}"),
        ("Candle", f"{b['time']:%H:%M} broker time"),
        ("Delay", f"{delay:.0f}s after candle close"),
    ]))


def manage(df):
    """Runs once per new closed candle: cancel stale orders, report fills and exits."""
    global pending
    if not pending:
        log("PEND", "none (flat, scanning for breakout)")
        return
    t, last = pending["ticket"], df.iloc[-1]
    side = "BUY" if pending["dir"] == 1 else "SELL"
    
    if mt5.orders_get(ticket=t):                                        # still waiting
        pending["bars"] += 1
        back = last.close < pending["bottom"] if pending["dir"] == 1 else last.close > pending["top"]
        log("PEND", f"ticket {t} waiting | candles waited={pending['bars']}/{MAX_WAIT_BARS} "
                    f"| close={px(last.close)} | closed back through zone={back}")
        if pending["bars"] % 5 == 0:
            tg(card(f"⏳ <b>{SYMBOL}</b> · {side} waiting", [("Candles", f"{pending['bars']}/{MAX_WAIT_BARS}"),
                                                          ("Close", px(last.close)), ("Back", str(back))]))
        if back or pending["bars"] > MAX_WAIT_BARS:
            r = mt5.order_send({"action": mt5.TRADE_ACTION_REMOVE, "order": t})
            why = "price closed back through zone" if back else "expired"
            log("PEND", f"cancel retcode={r.retcode} ({why})")
            tg(card(f"⚪ <b>{SYMBOL}</b> · {side} order cancelled", [("Why", why)]))
            pending = None
    elif mt5.positions_get(ticket=t):
        p = mt5.positions_get(ticket=t)[0]
        if not pending["filled"]:
            pending["filled"] = True
            log("FILL", f"ticket {t} filled @ {px(p.price_open)}")
            tg(card(f"✅ <b>{SYMBOL}</b> · {side} filled", [("Price", px(p.price_open)),
                                                           ("SL", px(p.sl)), ("TP", px(p.tp))]))
        else:
            log("FILL", f"position open | floating P/L={p.profit:+.2f} | sl={px(p.sl)} tp={px(p.tp)}")
            
            pending["held"] = pending.get("held", 0) + 1
            if pending["held"] % 5 == 0:
                tg(card(f"📈 <b>{SYMBOL}</b> · {side} open", [("P/L", f"{p.profit:+.2f}"), ("SL", px(p.sl)), ("TP", px(p.tp))]))

            if (p.sl, p.tp) != (pending.get("sl"), pending.get("tp")) and pending.get("sl") is not None:
                tg(card(f"🔧 <b>{SYMBOL}</b> · {side} SL/TP changed", [("SL", px(p.sl)), ("TP", px(p.tp))]))
            
            pending["sl"], pending["tp"] = p.sl, p.tp

    elif pending["filled"]:                                             # position gone = SL or TP hit
        deals = mt5.history_deals_get(position=t) or []
        pnl = sum(d.profit + d.commission + d.swap for d in deals)
        out = [d for d in deals if d.entry == mt5.DEAL_ENTRY_OUT]
        reason = {mt5.DEAL_REASON_TP: "TP hit", mt5.DEAL_REASON_SL: "SL hit"}.get(
            out[-1].reason if out else None, "closed")
        bal = mt5.account_info().balance
        log("CLOSE", f"ticket {t} closed | deals={len(deals)} | P/L={pnl:+.2f} | {reason}")
        tg(card(f"{'🎯' if pnl > 0 else '🛑'} <b>{SYMBOL}</b> · {side} {reason}",
                [("P/L", f"{pnl:+,.2f}"), ("Bal", f"{bal:,.2f}")]))
        pending = None
    else:
        log("PEND", f"ticket {t} no longer an order or position (removed outside the script), resetting")
        tg(card(f"⚪ <b>{SYMBOL}</b> · {side} order removed", [("Why", "removed outside the script")]))
        pending = None


def log_state():
    acc = mt5.account_info()
    ords = [o for o in (mt5.orders_get(symbol=SYMBOL) or []) if o.magic == MAGIC]
    poss = [p for p in (mt5.positions_get(symbol=SYMBOL) or []) if p.magic == MAGIC]
    log("STATE", f"balance={acc.balance:,.2f} equity={acc.equity:,.2f} | broker pending orders={len(ords)} "
                 f"open positions={len(poss)} | tracked={'ticket ' + str(pending['ticket']) if pending else 'none'} "
                 f"| zones traded this session={len(traded)}")


# ---------- main loop ----------
def main():
    global DIGITS
    log("INIT", "connecting to MT5...")
    if not mt5.initialize():
        raise SystemExit(f"MT5 init failed: {mt5.last_error()}")
    acc, term, info = mt5.account_info(), mt5.terminal_info(), mt5.symbol_info(SYMBOL)
    if info is None:
        raise SystemExit(f"Symbol {SYMBOL} not found at this broker (try a suffix like {SYMBOL}.m)")
    DIGITS = info.digits
    is_demo = acc.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO
    log("INIT", f"account={acc.login} server={acc.server} mode={'DEMO' if is_demo else 'LIVE/CONTEST'} "
                f"leverage=1:{acc.leverage} balance={acc.balance:,.2f} {acc.currency}")
    log("INIT", f"{SYMBOL}: digits={info.digits} stops_level={info.trade_stops_level} "
                f"lots min/step/max={info.volume_min}/{info.volume_step}/{info.volume_max} spread={info.spread} pts")
    log("INIT", f"algo trading enabled in terminal: {term.trade_allowed}")
    if not is_demo and not ALLOW_LIVE:
        raise SystemExit("Not a demo account. Set ALLOW_LIVE = True to override.")
    if not term.trade_allowed:
        log("INIT", "WARNING: enable 'Algo Trading' in the MT5 terminal or orders will be rejected")
    
    mt5.symbol_select(SYMBOL, True)

    log("INIT", f"config: M1 | swing n={SWING_N} | risk={RISK_PCT:.0%} | RR=1:{RR:g} | SL buffer={SL_BUFFER:.2%} "
                f"| max wait={MAX_WAIT_BARS} candles")
    tg(card("🚀 <b>Bot started</b>", [
        ("Pair", f"{SYMBOL} · M1 · {'DEMO' if is_demo else 'LIVE'}"),
        ("Bal", f"{acc.balance:,.2f} {acc.currency}"),
        ("Risk", f"{RISK_PCT:.0%} per trade · RR 1:{RR:g}"),
    ]))

    last_seen, last_hb, last_err = None, time.time(), 0
    while True:
        try:
            raw = fetch_data()
            if raw is not None:
                df = clean_ohlc(raw)
                if df.index[-1] != last_seen:                           # new closed candle
                    first = last_seen is None
                    last_seen = df.index[-1]
                    c = df.iloc[-1]
                    log("CANDLE", f"{last_seen:%Y-%m-%d %H:%M} O={px(c.open)} H={px(c.high)} L={px(c.low)} "
                                  f"C={px(c.close)} | {len(df)} candles loaded" + (" (first load)" if first else ""))
                    manage(df)

                    lag = mt5.symbol_info_tick(SYMBOL).time - (last_seen.timestamp() + 60)
                    if lag > 90:
                        tg_once(("lag", last_seen), card(f"⏱ <b>{SYMBOL}</b> · delayed data", [("Lag", f"{lag:.0f}s"), ("Candle", f"{last_seen:%H:%M}")]))

                    b = detect_breakout(df)
                    if b:
                        key = (round(b["top"], 5), round(b["bottom"], 5), b["dir"])
                        up = b["dir"] == 1
                        if pending and pending["dir"] != b["dir"]:
                            state = (f"AGAINST open {'BUY' if pending['dir'] == 1 else 'SELL'} "
                                     f"#{pending['ticket']} ({'filled' if pending['filled'] else 'pending'})")
                        elif pending:
                            state = f"same direction as active #{pending['ticket']}"
                        elif key in traded:
                            state = "zone already traded"
                        else:
                            state = "no active trade, placing order"
                        tg_once(("sig", key), card(f"📣 <b>{SYMBOL}</b> · {'UPSIDE' if up else 'DOWNSIDE'} breakout", [
                            ("Close", px(df.iloc[-1].close)),
                            ("Zone", f"{px(b['bottom'])} - {px(b['top'])}"),
                            ("Candle", f"{b['time']:%H:%M}"),
                            ("Status", state)]))
                        if pending:
                            log("SKIP", "breakout ignored: an order/position is already active")
                            tg_once(("skipA", key), card(f"⏭ <b>{SYMBOL}</b> · breakout skipped", [("Why", "order/position already active")]))
                        elif key in traded:
                            log("SKIP", "breakout ignored: this zone was already traded")
                            tg_once(("skipT", key), card(f"⏭ <b>{SYMBOL}</b> · breakout skipped", [("Why", "zone already traded")]))
                        else:
                            traded.add(key)
                            execute(b)
                    log_state()
                    last_hb = time.time()
                elif time.time() - last_hb >= HEARTBEAT_SEC:
                    t = mt5.symbol_info_tick(SYMBOL)
                    log("WAIT", f"no new candle since {last_seen:%H:%M} | bid={px(t.bid)} ask={px(t.ask)}")
                    last_hb = time.time()
        except Exception as e:
            msg = f"{type(e).__name__}: {e}"
            log("ERROR", msg)
            if time.time() - last_err > 300:                            # max one error message per 5 min
                last_err = time.time()
                send_tg(card("⚠️ <b>Bot error</b>", [("Err", msg[:300])]))
        time.sleep(2)


if __name__ == "__main__":
    main()
