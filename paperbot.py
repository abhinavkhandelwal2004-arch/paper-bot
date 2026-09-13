import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, time as dtime
import time, json, os, requests, pytz

# ============ TUMHARI DETAILS (already filled) ============
TOKEN = "8919842664:AAETGXag3sLOBTHICEOOFRe2j1ug3mXcb_0"
CHAT_ID = "5606330617"
# =========================================================

def send_telegram(msg):
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                     params={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except:
        pass

CAPITAL_FILE = "capital.json"
LOG_FILE = "trades.csv"
CAPITAL_START = 2000.0
RISK_PER_TRADE = 0.01
DAILY_LOSS_LIMIT = 0.02
MAX_TRADES_PER_DAY = 2
MIN_NET_PROFIT = 8.0

WATCHLIST = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
             "SBIN.NS", "ITC.NS", "LT.NS", "AXISBANK.NS", "KOTAKBANK.NS",
             "BHARTIARTL.NS", "HINDUNILVR.NS", "MARUTI.NS", "ASIANPAINT.NS", "TITAN.NS"]


def calc_charges(buy_price, sell_price, qty):
    buy_val = buy_price * qty
    sell_val = sell_price * qty
    turnover = buy_val + sell_val
    brokerage = 0.0
    stt = 0.001 * sell_val
    exch_txn = 0.0000325 * turnover
    gst = 0.18 * (brokerage + exch_txn)
    sebi = 0.000001 * turnover
    stamp = 0.00015 * buy_val
    dp_charges = 13.5
    return round(brokerage + stt + exch_txn + gst + sebi + stamp + dp_charges, 2)


def load_state():
    if os.path.exists(CAPITAL_FILE):
        with open(CAPITAL_FILE) as f:
            return json.load(f)
    return {"capital": CAPITAL_START, "date": str(datetime.now().date()),
            "trades_today": 0, "loss_today": 0.0, "open_position": None}


def save_state(s):
    with open(CAPITAL_FILE, "w") as f:
        json.dump(s, f, indent=2)


def log_trade(row):
    df = pd.DataFrame([row])
    if os.path.exists(LOG_FILE):
        df.to_csv(LOG_FILE, mode="a", header=False, index=False)
    else:
        df.to_csv(LOG_FILE, index=False)


def get_signal(symbol):
    try:
        df = yf.download(symbol, period="5d", interval="15m",
                         progress=False, auto_adjust=True)
        if df is None or len(df) < 50:
            return None
        df["EMA20"] = df["Close"].ewm(span=20).mean()
        df["EMA50"] = df["Close"].ewm(span=50).mean()
        delta = df["Close"].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = -delta.clip(upper=0).rolling(14).mean()
        rs = gain / loss
        df["RSI"] = 100 - (100 / (1 + rs))
        last = df.iloc[-1]
        price = float(last["Close"])
        ema20 = float(last["EMA20"])
        ema50 = float(last["EMA50"])
        rsi = float(last["RSI"])
        if price > ema20 > ema50 and 40 < rsi < 65:
            return {"symbol": symbol, "price": price, "sl": price * 0.985, "rsi": rsi}
        return None
    except:
        return None


def run_scan():
    state = load_state()
    today = str(datetime.now().date())
    if state["date"] != today:
        state["date"] = today
        state["trades_today"] = 0
        state["loss_today"] = 0.0
        save_state(state)
        send_telegram(f"☀️ *Naya din shuru*\nCapital: ₹{state['capital']:.2f}")

    if state["loss_today"] >= DAILY_LOSS_LIMIT * CAPITAL_START:
        send_telegram("❌ Daily loss limit hit. Aaj trading band.")
        return
    if state["trades_today"] >= MAX_TRADES_PER_DAY:
        return
    if state["open_position"]:
        manage_open_position(state)
        return

    for sym in WATCHLIST:
        sig = get_signal(sym)
        if not sig:
            continue
        price = sig["price"]
        sl = sig["sl"]
        risk_per_share = price - sl
        if risk_per_share <= 0:
            continue
        qty = int((state["capital"] * RISK_PER_TRADE) / risk_per_share)
        if qty < 1:
            continue
        cost = price * qty
        if cost > state["capital"]:
            qty = int(state["capital"] // price)
        if qty < 1:
            continue
        target_price = price * 1.02
        est_charges = calc_charges(price, target_price, qty)
        est_net = (target_price - price) * qty - est_charges
        if est_net < MIN_NET_PROFIT:
            continue
        state["open_position"] = {"symbol": sym, "entry": price, "qty": qty,
                                   "sl": sl, "trail_high": price,
                                   "target": target_price,
                                   "entry_time": str(datetime.now())}
        state["capital"] -= cost
        save_state(state)
        send_telegram(f"📈 *PAPER BUY*\nStock: {sym}\nPrice: ₹{price:.2f}\nQty: {qty}\nCost: ₹{cost:.2f}\nSL: ₹{sl:.2f}\nTarget: ₹{target_price:.2f}")
        return


def manage_open_position(state):
    pos = state["open_position"]
    sym = pos["symbol"]
    try:
        df = yf.download(sym, period="1d", interval="5m",
                         progress=False, auto_adjust=True)
        if df is None or len(df) == 0:
            return
        price = float(df["Close"].iloc[-1])
    except:
        return

    if price > pos["trail_high"]:
        pos["trail_high"] = price
        new_sl = max(pos["sl"], price * 0.99)
        if new_sl > pos["sl"]:
            pos["sl"] = new_sl
            save_state(state)
            send_telegram(f"↑ *Trailing SL Updated*\nStock: {sym}\nNew SL: ₹{new_sl:.2f}")

    exit_price = None
    reason = None
    if price <= pos["sl"]:
        exit_price = price
        reason = "Trailing SL hit"
    elif price >= pos["target"]:
        exit_price = price
        reason = "Target hit"

    if not exit_price:
        return

    gross = (exit_price - pos["entry"]) * pos["qty"]
    charges = calc_charges(pos["entry"], exit_price, pos["qty"])
    net = gross - charges
    state["capital"] += net
    state["trades_today"] += 1
    if net < 0:
        state["loss_today"] += abs(net)

    log_trade({"date": str(datetime.now().date()),
               "time": str(datetime.now().time()),
               "symbol": sym, "entry": pos["entry"], "qty": pos["qty"],
               "exit": exit_price, "gross": round(gross, 2),
               "charges": charges, "net": round(net, 2),
               "reason": reason, "capital_after": round(state["capital"], 2)})

    emoji = "✅" if net > 0 else "❌"
    send_telegram(f"{emoji} *PAPER SELL*\nStock: {sym}\nExit: ₹{exit_price:.2f}\nReason: {reason}\nGross: ₹{gross:.2f}\nCharges: ₹{charges}\nNet: ₹{net:.2f}\nNew Capital: ₹{state['capital']:.2f}")

    state["open_position"] = None
    save_state(state)


if __name__ == "__main__":
    send_telegram("🤖 Paper Trading Bot *ONLINE* ho gaya. Ab daily scan karega.")
    while True:
        try:
            now = datetime.now(pytz.timezone("Asia/Kolkata")).time()
            if dtime(9, 20) <= now <= dtime(15, 0):
                run_scan()
            time.sleep(900)
        except KeyboardInterrupt:
            break
        except Exception as e:
            send_telegram(f"⚠️ Error: {e}")
            time.sleep(60)
