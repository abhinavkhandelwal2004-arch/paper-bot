import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import time, json, os, requests

# ============ TUMHARI DETAILS ============
TOKEN = "8919842664:AAETGXag3sLOBTHICEOOFRe2j1ug3mXcb_0"
CHAT_ID = "5606330617"
# =========================================

def send_telegram(msg):
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                     params={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except:
        pass

CAPITAL_FILE = "crypto_capital.json"
LOG_FILE = "crypto_trades.csv"
CAPITAL_START = 24.0        # ~₹2000 in USD
RISK_PER_TRADE = 0.02       # 2% per trade ($0.48)
DAILY_LOSS_LIMIT = 0.05     # 5% daily loss limit
MAX_TRADES_PER_DAY = 3
MIN_NET_PROFIT = 0.10       # $0.10 minimum net profit
CRYPTO_FEE_PCT = 0.005      # 0.5% per side

WATCHLIST = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
             "ADA-USD", "DOGE-USD", "AVAX-USD", "LINK-USD", "LTC-USD"]


def calc_charges(buy_price, sell_price, qty):
    buy_val = buy_price * qty
    sell_val = sell_price * qty
    buy_fee = buy_val * CRYPTO_FEE_PCT
    sell_fee = sell_val * CRYPTO_FEE_PCT
    gst = 0.18 * (buy_fee + sell_fee)
    return round(buy_fee + sell_fee + gst, 4)


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

        close = df["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]

        df["EMA20"] = close.ewm(span=20).mean()
        df["EMA50"] = close.ewm(span=50).mean()

        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = -delta.clip(upper=0).rolling(14).mean()
        rs = gain / loss
        df["RSI"] = 100 - (100 / (1 + rs))

        last = df.iloc[-1]
        price = float(last["Close"])
        ema20 = float(last["EMA20"])
        ema50 = float(last["EMA50"])
        rsi = float(last["RSI"])

        if price > ema20 > ema50 and 40 < rsi < 70:
            return {"symbol": symbol, "price": price, "sl": price * 0.98, "rsi": rsi}
        return None
    except Exception as e:
        print(f"[skip] {symbol}: {e}")
        return None


def run_scan():
    state = load_state()
    today = str(datetime.now().date())

    if state["date"] != today:
        state["date"] = today
        state["trades_today"] = 0
        state["loss_today"] = 0.0
        save_state(state)
        send_telegram(f"🪙 *Crypto bot — naya din*\nCapital: ${state['capital']:.2f}")

    if state["loss_today"] >= DAILY_LOSS_LIMIT * CAPITAL_START:
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

        # Fractional quantity
        qty = round((state["capital"] * RISK_PER_TRADE) / risk_per_share, 6)
        if qty <= 0:
            continue

        cost = price * qty
        if cost > state["capital"]:
            qty = round(state["capital"] / price * 0.95, 6)
            cost = price * qty
        if qty <= 0:
            continue

        target_price = price * 1.03
        est_charges = calc_charges(price, target_price, qty)
        est_net = (target_price - price) * qty - est_charges

        if est_net < MIN_NET_PROFIT:
            continue

        state["open_position"] = {
            "symbol": sym, "entry": price, "qty": qty,
            "sl": sl, "trail_high": price,
            "target": target_price,
            "entry_time": str(datetime.now())
        }
        state["capital"] -= cost
        save_state(state)

        send_telegram(
            f"🪙 *CRYPTO PAPER BUY*\n"
            f"Coin: {sym}\n"
            f"Price: ${price:.4f}\n"
            f"Qty: {qty}\n"
            f"Cost: ${cost:.4f}\n"
            f"SL: ${sl:.4f}\n"
            f"Target: ${target_price:.4f}"
        )
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

    # Trailing SL update
    if price > pos["trail_high"]:
        pos["trail_high"] = price
        new_sl = max(pos["sl"], price * 0.985)
        if new_sl > pos["sl"]:
            pos["sl"] = new_sl
            save_state(state)
            send_telegram(f"↑ *Trailing SL Updated*\nCoin: {sym}\nNew SL: ${new_sl:.4f}")

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

    log_trade({
        "date": str(datetime.now().date()),
        "time": str(datetime.now().time()),
        "symbol": sym, "entry": pos["entry"], "qty": pos["qty"],
        "exit": exit_price, "gross": round(gross, 4),
        "charges": charges, "net": round(net, 4),
        "reason": reason, "capital_after": round(state["capital"], 4)
    })

    emoji = "✅" if net > 0 else "❌"
    send_telegram(
        f"{emoji} *CRYPTO PAPER SELL*\n"
        f"Coin: {sym}\n"
        f"Entry: ${pos['entry']:.4f}\n"
        f"Exit: ${exit_price:.4f}\n"
        f"Qty: {pos['qty']}\n"
        f"Reason: {reason}\n"
        f"Gross: ${gross:.4f}\n"
        f"Charges: ${charges}\n"
        f"Net: ${net:.4f}\n"
        f"Capital: ${state['capital']:.4f}"
    )

    state["open_position"] = None
    save_state(state)


if __name__ == "__main__":
    send_telegram("🪙 *Crypto Paper Bot ONLINE*\n24/7 chalega. Weekend bhi.")
    while True:
        try:
            run_scan()
            time.sleep(900)
        except KeyboardInterrupt:
            break
        except Exception as e:
            send_telegram(f"⚠️ Crypto bot error: {e}")
            time.sleep(60)
