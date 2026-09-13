"""
AI Paper Trading Bot v7.3 — QUICK PROFIT DELIVERY MODE
Bug Fixes: double manage, daily reset, momentum save, multi-entry, entry_dt fallback
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, time as dtime, timedelta
import time, json, os, requests, pytz
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# ==================== CONFIGURATION =========================
# ============================================================
TOKEN = "8919842664:AAEcxSad6guNmcqPwlBFn_BBtwAAvrB8Ac8"
CHAT_ID = "5606330617"

CAPITAL_START = 5000.0
CAPITAL_MODE = "DELIVERY"
RISK_PER_TRADE_PCT = 0.015
DAILY_LOSS_LIMIT_PCT = 0.03
MAX_DRAWDOWN_PCT = 0.12
MAX_POSITIONS = 3
MAX_TRADES_PER_DAY = 4
MIN_SIGNAL_SCORE = 5

TARGET_1_R_MULTIPLE = 1.0
TARGET_2_R_MULTIPLE = 2.0
PARTIAL_BOOK_PCT = 0.6
TRAIL_PCT_AFTER_1R = 0.008
TRAIL_PCT_BEFORE_1R = 0.012
HOLD_DAYS_MAX = 3
NO_MOVE_EXIT_HOURS = 36
MOMENTUM_BOOST_R = 1.5

STT_DELIVERY_PCT = 0.001
EXCHANGE_TXN_PCT = 0.0000322
SEBI_FEE_PCT = 0.000001
STAMP_DUTY_BUY = 0.00015
DP_CHARGES = 13.5
GST_PCT = 0.18

MIN_PROFIT_MULTIPLIER = 3
AUTO_DISABLE_AFTER_LOSSES = 3
STRATEGY_MIN_WINRATE = 0.35

# ============================================================
# ==================== STOCK UNIVERSE ========================
# ============================================================
NSE_STOCKS = [
    "RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS","SBIN.NS",
    "ITC.NS","LT.NS","AXISBANK.NS","KOTAKBANK.NS","BHARTIARTL.NS","HINDUNILVR.NS",
    "MARUTI.NS","ASIANPAINT.NS","TITAN.NS","BAJFINANCE.NS","HCLTECH.NS","WIPRO.NS",
    "TECHM.NS","SUNPHARMA.NS","TATAMOTORS.NS","TATASTEEL.NS","JSWSTEEL.NS",
    "POWERGRID.NS","NTPC.NS","ONGC.NS","COALINDIA.NS","DRREDDY.NS","CIPLA.NS",
    "ULTRACEMCO.NS","ADANIENT.NS","ADANIPORTS.NS","BAJAJFINSV.NS","BAJAJ-AUTO.NS",
    "GRASIM.NS","HEROMOTOCO.NS","HINDALCO.NS","INDUSINDBK.NS","M&M.NS",
    "NESTLEIND.NS","SHREECEM.NS","TATACONSUM.NS","DIVISLAB.NS","BRITANNIA.NS",
    "EICHERMOT.NS","APOLLOHOSP.NS","BPCL.NS","IOC.NS","PIDILITIND.NS",
    "DABUR.NS","GODREJCP.NS","MARICO.NS","BERGEPAINT.NS","HAVELLS.NS",
    "SIEMENS.NS","DMART.NS","BAJAJHLDNG.NS","AMBUJACEM.NS","BANKBARODA.NS",
    "PNB.NS","CANBK.NS","IDFCFIRSTB.NS","FEDERALBNK.NS","BANDHANBNK.NS",
    "RBLBANK.NS","AUBANK.NS","INDIGO.NS","TRENT.NS","VEDL.NS",
    "GAIL.NS","MOTHERSON.NS","BOSCHLTD.NS","ABBOTINDIA.NS","PGHH.NS",
    "COLPAL.NS","UBL.NS","JUBLFOOD.NS","PAGEIND.NS",
    "LICI.NS","IRCTC.NS","ZOMATO.NS","NYKAA.NS","PAYTM.NS",
    "POLICYBZR.NS","DELHIVERY.NS","CAMS.NS","KPITTECH.NS","PERSISTENT.NS",
    "LTIM.NS","MPHASIS.NS","COFORGE.NS","TATAELXSI.NS","LTTS.NS",
    "BEL.NS","HAL.NS","BHEL.NS","CONCOR.NS","RECLTD.NS",
    "PFC.NS","IRFC.NS","RVNL.NS","IRCON.NS","NBCC.NS"
]

BSE_STOCKS = [
    "RELIANCE.BO","TCS.BO","HDFCBANK.BO","INFY.BO","ICICIBANK.BO","SBIN.BO",
    "ITC.BO","LT.BO","AXISBANK.BO","KOTAKBANK.BO","BHARTIARTL.BO","HINDUNILVR.BO",
    "MARUTI.BO","ASIANPAINT.BO","TITAN.BO","BAJFINANCE.BO","HCLTECH.BO","WIPRO.BO",
    "SUNPHARMA.BO","TATAMOTORS.BO","TATASTEEL.BO","POWERGRID.BO","NTPC.BO",
    "ONGC.BO","COALINDIA.BO","DRREDDY.BO","CIPLA.BO","ULTRACEMCO.BO",
    "ADANIENT.BO","ADANIPORTS.BO","GRASIM.BO","HEROMOTOCO.BO","HINDALCO.BO",
    "INDUSINDBK.BO","M&M.BO","NESTLEIND.BO","SHREECEM.BO","TATACONSUM.BO",
    "BRITANNIA.BO","EICHERMOT.BO","APOLLOHOSP.BO","BPCL.BO","IOC.BO",
    "PIDILITIND.BO","DABUR.BO","GODREJCP.BO","MARICO.BO","HAVELLS.BO",
    "SIEMENS.BO","DMART.BO","BANKBARODA.BO","PNB.BO","CANBK.BO",
    "GAIL.BO","VEDL.BO","BEL.BO","HAL.BO","BHEL.BO"
]

def build_universe():
    seen = set(); combined = []
    for s in NSE_STOCKS:
        base = s.replace(".NS", "")
        if base not in seen:
            seen.add(base); combined.append(s)
    for s in BSE_STOCKS:
        base = s.replace(".BO", "")
        if base not in seen:
            seen.add(base); combined.append(s)
    return combined

WATCHLIST = build_universe()

STRATEGY_NAMES = [
    "ORB", "VWAP_PULLBACK", "EMA_CROSS", "SUPERTREND_ADX", "BB_SQUEEZE",
    "RSI_DIVERGENCE", "CPR", "MACD_RSI", "INSIDE_BAR", "STOCHRSI_ST",
    "MOMENTUM_BREAKOUT", "VOLUME_SPIKE", "KELTNER_BREAKOUT", "DONCHIAN_BREAKOUT",
    "PSAR_TREND", "HEIKIN_ASHI", "ENGULFING", "HAMMER_STAR", "MEAN_REVERSION",
    "MULTI_EMA_TREND"
]

# ============================================================
# ==================== HELPERS ===============================
# ============================================================
IST = pytz.timezone("Asia/Kolkata")
CAPITAL_FILE = "capital.json"
LOG_FILE = "trades.csv"
STRATEGY_STATS_FILE = "strategy_stats.json"

def send_telegram(msg):
    try:
        r = requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                         params={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"},
                         timeout=10)
        if r.status_code != 200:
            print(f"[TG Error] {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"[TG Exception] {e}")

def send_document(filepath, caption=""):
    try:
        if not os.path.exists(filepath): return
        with open(filepath, "rb") as f:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendDocument",
                          data={"chat_id": CHAT_ID, "caption": caption},
                          files={"document": f}, timeout=30)
    except Exception as e:
        print(f"[Doc Error] {e}")

def calc_charges(buy_price, sell_price, qty):
    buy_val = buy_price * qty
    sell_val = sell_price * qty
    turnover = buy_val + sell_val
    stt = STT_DELIVERY_PCT * (buy_val + sell_val)
    exch = EXCHANGE_TXN_PCT * turnover
    sebi = SEBI_FEE_PCT * turnover
    stamp = STAMP_DUTY_BUY * buy_val
    dp = DP_CHARGES
    gst = GST_PCT * (exch + sebi)
    return round(stt + exch + sebi + stamp + dp + gst, 2)

def min_required_net_profit():
    est = calc_charges(500, 505, 5)
    return max(12.0, est * MIN_PROFIT_MULTIPLIER)

# ============================================================
# ==================== STATE =================================
# ============================================================
def load_state():
    default = {
        "capital": CAPITAL_START,
        "starting_capital": CAPITAL_START,
        "peak_capital": CAPITAL_START,
        "date": str(datetime.now(IST).date()),
        "trades_today": 0,
        "loss_today": 0.0,
        "open_positions": [],
        "disabled_today": [],
        "last_daily": "", "last_weekly": "", "last_monthly": "",
        "drawdown_alerted": ""
    }
    if os.path.exists(CAPITAL_FILE):
        try:
            with open(CAPITAL_FILE) as f:
                state = json.load(f)
            for k, v in default.items():
                state.setdefault(k, v)
            if not isinstance(state.get("open_positions"), list):
                state["open_positions"] = []
            return state
        except Exception as e:
            print(f"[State Load Error] {e}")
            return default.copy()
    return default.copy()

def save_state(s):
    try:
        s["open_positions"] = list(s.get("open_positions", []))
        s["disabled_today"] = list(s.get("disabled_today", []))
        with open(CAPITAL_FILE, "w") as f:
            json.dump(s, f, indent=2, default=str)
    except Exception as e:
        print(f"[State Save Error] {e}")

def daily_reset_if_needed(state):
    """FIX: Separate function - called first in main loop"""
    today = str(datetime.now(IST).date())
    if state["date"] != today:
        state["date"] = today
        state["trades_today"] = 0
        state["loss_today"] = 0.0
        state["disabled_today"] = []
        state["drawdown_alerted"] = ""
        save_state(state)
        return True, today
    return False, today

def load_strategy_stats():
    stats = {}
    if os.path.exists(STRATEGY_STATS_FILE):
        try:
            with open(STRATEGY_STATS_FILE) as f:
                stats = json.load(f)
        except: stats = {}
    for s in STRATEGY_NAMES:
        if s not in stats or not isinstance(stats.get(s), dict):
            stats[s] = {"wins":0,"losses":0,"pnl":0.0,"streak_losses":0,"total":0}
        else:
            stats[s].setdefault("wins", 0); stats[s].setdefault("losses", 0)
            stats[s].setdefault("pnl", 0.0); stats[s].setdefault("streak_losses", 0)
            stats[s].setdefault("total", 0)
    return stats

def save_strategy_stats(stats):
    try:
        with open(STRATEGY_STATS_FILE, "w") as f:
            json.dump(stats, f, indent=2)
    except Exception as e:
        print(f"[Stats Save] {e}")

def log_trade(row):
    try:
        df = pd.DataFrame([row])
        if os.path.exists(LOG_FILE):
            df.to_csv(LOG_FILE, mode="a", header=False, index=False)
        else:
            df.to_csv(LOG_FILE, index=False)
    except Exception as e:
        print(f"[Log Error] {e}")

def safe_parse_dt(s):
    """FIX: Safe datetime parsing with fallback"""
    if not s: return None
    try:
        return datetime.fromisoformat(s)
    except:
        try:
            return datetime.strptime(s, "%Y-%m-%d %H:%M:%S.%f%z")
        except:
            try:
                return datetime.strptime(s, "%Y-%m-%d %H:%M:%S.%f")
            except:
                return None

# ============================================================
# ==================== DATA ==================================
# ============================================================
def _flatten(df):
    if df is None: return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def fetch_daily(symbol):
    try:
        df = yf.download(symbol, period="90d", interval="1d",
                         progress=False, auto_adjust=True)
        df = _flatten(df)
        if df is None or len(df) < 50: return None
        return df
    except: return None

def fetch_intraday(symbol):
    try:
        df = yf.download(symbol, period="5d", interval="15m",
                         progress=False, auto_adjust=True)
        df = _flatten(df)
        if df is None or len(df) < 5: return None
        return df
    except: return None

def add_indicators(df):
    df["EMA9"] = df["Close"].ewm(span=9).mean()
    df["EMA21"] = df["Close"].ewm(span=21).mean()
    df["EMA50"] = df["Close"].ewm(span=50).mean()
    df["EMA200"] = df["Close"].ewm(span=200).mean()

    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI"] = (100 - (100 / (1 + rs))).fillna(50)

    df["TR"] = df[["High","Low","Close"]].apply(
        lambda x: max(x["High"]-x["Low"], abs(x["High"]-x["Close"]), abs(x["Low"]-x["Close"])), axis=1)
    df["ATR"] = df["TR"].rolling(14).mean().fillna(df["TR"].rolling(5).mean()).fillna(0)

    plus_dm = df["High"].diff().clip(lower=0)
    minus_dm = (-df["Low"].diff()).clip(lower=0)
    tr14 = df["TR"].rolling(14).sum().replace(0, np.nan)
    plus_di = 100 * (plus_dm.rolling(14).sum() / tr14)
    minus_di = 100 * (minus_dm.rolling(14).sum() / tr14)
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)
    df["ADX"] = dx.rolling(14).mean().fillna(0)
    df["PLUS_DI"] = plus_di.fillna(0)
    df["MINUS_DI"] = minus_di.fillna(0)

    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    df["VWAP"] = ((tp * df["Volume"]).cumsum() / df["Volume"].cumsum().replace(0, np.nan)).fillna(df["Close"])

    df["MA20"] = df["Close"].rolling(20).mean()
    df["STD20"] = df["Close"].rolling(20).std().fillna(0)
    df["BB_Upper"] = df["MA20"] + 2 * df["STD20"]
    df["BB_Lower"] = df["MA20"] - 2 * df["STD20"]
    df["BB_Width"] = (df["BB_Upper"] - df["BB_Lower"]) / df["MA20"]
    df["BB_AvgWidth"] = df["BB_Width"].rolling(20).mean()

    df["ST_Upper"] = (df["High"] + df["Low"]) / 2 + 3 * df["ATR"]
    df["ST_Lower"] = (df["High"] + df["Low"]) / 2 - 3 * df["ATR"]

    ema12 = df["Close"].ewm(span=12).mean()
    ema26 = df["Close"].ewm(span=26).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=9).mean()

    rsi_min = df["RSI"].rolling(14).min()
    rsi_max = df["RSI"].rolling(14).max()
    df["StochRSI"] = (df["RSI"] - rsi_min) / (rsi_max - rsi_min + 0.0001) * 100
    df["K"] = df["StochRSI"].rolling(3).mean()
    df["D"] = df["K"].rolling(3).mean()

    df["KC_Upper"] = df["EMA21"] + 2 * df["ATR"]
    df["KC_Lower"] = df["EMA21"] - 2 * df["ATR"]
    df["DC_Upper"] = df["High"].rolling(20).max()
    df["DC_Lower"] = df["Low"].rolling(20).min()
    df["PSAR"] = df["Low"].rolling(5).min()

    df["Vol_MA20"] = df["Volume"].rolling(20).mean().replace(0, np.nan)
    df["Vol_Ratio"] = (df["Volume"] / df["Vol_MA20"]).fillna(1.0)

    df["HA_Close"] = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4
    df["HA_Open"] = (df["Open"].shift(1) + df["Close"].shift(1)) / 2
    df["HA_Bull"] = df["HA_Close"] > df["HA_Open"]
    return df

# ============================================================
# ==================== 20 STRATEGIES =========================
# ============================================================
def strat_orb(df, now_time):
    if len(df) < 2: return None
    try:
        last, prev = df.iloc[-1], df.iloc[-2]
        pdh, pdl = float(prev["High"]), float(prev["Low"])
        price = float(last["Close"]); atr = float(last["ATR"])
        if atr <= 0: return None
        if price > pdh * 1.005:
            return {"side":"BUY","price":price,"sl":max(pdl, price - atr*2),"score":6}
        if price < pdl * 0.995:
            return {"side":"SELL","price":price,"sl":min(pdh, price + atr*2),"score":6}
    except: pass
    return None

def strat_vwap(df, now_time):
    if len(df) < 2: return None
    last, prev = df.iloc[-1], df.iloc[-2]
    price = float(last["Close"]); vwap = float(last["VWAP"])
    pv = float(prev["VWAP"]); atr = float(last["ATR"])
    if atr <= 0: return None
    if float(prev["Close"]) < pv and price > vwap * 1.002:
        return {"side":"BUY","price":price,"sl":price - atr*2,"score":5}
    if float(prev["Close"]) > pv and price < vwap * 0.998:
        return {"side":"SELL","price":price,"sl":price + atr*2,"score":5}
    return None

def strat_ema_cross(df, now_time):
    if len(df) < 2: return None
    last, prev = df.iloc[-1], df.iloc[-2]
    price = float(last["Close"]); rsi = float(last["RSI"]); atr = float(last["ATR"])
    if atr <= 0: return None
    if float(prev["EMA9"]) <= float(prev["EMA21"]) and float(last["EMA9"]) > float(last["EMA21"]) and 50 < rsi < 72:
        return {"side":"BUY","price":price,"sl":price - atr*2,"score":5}
    if float(prev["EMA9"]) >= float(prev["EMA21"]) and float(last["EMA9"]) < float(last["EMA21"]) and 28 < rsi < 50:
        return {"side":"SELL","price":price,"sl":price + atr*2,"score":5}
    return None

def strat_supertrend_adx(df, now_time):
    last = df.iloc[-1]
    price = float(last["Close"]); adx = float(last["ADX"])
    if adx < 25: return None
    if price > float(last["ST_Lower"]) and float(last["EMA9"]) > float(last["EMA21"]) and float(last["PLUS_DI"]) > float(last["MINUS_DI"]):
        return {"side":"BUY","price":price,"sl":float(last["ST_Lower"]),"score":6}
    if price < float(last["ST_Upper"]) and float(last["EMA9"]) < float(last["EMA21"]) and float(last["MINUS_DI"]) > float(last["PLUS_DI"]):
        return {"side":"SELL","price":price,"sl":float(last["ST_Upper"]),"score":6}
    return None

def strat_bb_squeeze(df, now_time):
    last = df.iloc[-1]
    price = float(last["Close"])
    if float(last["ADX"]) > 20: return None
    bw = float(last["BB_Width"]); aw = float(last["BB_AvgWidth"])
    if pd.isna(bw) or pd.isna(aw) or bw >= aw: return None
    if price > float(last["BB_Upper"]):
        return {"side":"BUY","price":price,"sl":float(last["MA20"]),"score":5}
    if price < float(last["BB_Lower"]):
        return {"side":"SELL","price":price,"sl":float(last["MA20"]),"score":5}
    return None

def strat_rsi_divergence(df, now_time):
    if len(df) < 30: return None
    last = df.iloc[-1]; price = float(last["Close"])
    lb = 10
    prev_low = float(df["Low"].iloc[-lb:-1].min())
    prev_high = float(df["High"].iloc[-lb:-1].max())
    prev_rsi_low = float(df["RSI"].iloc[-lb:-1].min())
    prev_rsi_high = float(df["RSI"].iloc[-lb:-1].max())
    rsi = float(last["RSI"]); atr = float(last["ATR"])
    if atr <= 0: return None
    if float(last["Low"]) < prev_low and rsi > prev_rsi_low + 3:
        return {"side":"BUY","price":price,"sl":price - atr*1.5,"score":5}
    if float(last["High"]) > prev_high and rsi < prev_rsi_high - 3:
        return {"side":"SELL","price":price,"sl":price + atr*1.5,"score":5}
    return None

def strat_cpr(df, now_time):
    if len(df) < 2: return None
    prev = df.iloc[-2]
    ph, pl, pc = float(prev["High"]), float(prev["Low"]), float(prev["Close"])
    pivot = (ph + pl + pc) / 3
    bc = (ph + pl) / 2; tc = (pivot - bc) + pivot
    last = df.iloc[-1]
    price = float(last["Close"]); atr = float(last["ATR"])
    if atr <= 0: return None
    if abs(tc - bc) > 0.002 * price: return None
    if price > max(tc, bc) and float(last["Close"]) > float(last["Open"]):
        return {"side":"BUY","price":price,"sl":min(pivot, price-atr*2),"score":5}
    if price < min(tc, bc) and float(last["Close"]) < float(last["Open"]):
        return {"side":"SELL","price":price,"sl":max(pivot, price+atr*2),"score":5}
    return None

def strat_macd_rsi(df, now_time):
    if len(df) < 2: return None
    last, prev = df.iloc[-1], df.iloc[-2]
    price = float(last["Close"]); rsi = float(last["RSI"]); atr = float(last["ATR"])
    if atr <= 0: return None
    up = float(prev["MACD"]) <= float(prev["MACD_Signal"]) and float(last["MACD"]) > float(last["MACD_Signal"])
    dn = float(prev["MACD"]) >= float(prev["MACD_Signal"]) and float(last["MACD"]) < float(last["MACD_Signal"])
    if up and 50 < rsi < 72: return {"side":"BUY","price":price,"sl":price - atr*2,"score":4}
    if dn and 28 < rsi < 50: return {"side":"SELL","price":price,"sl":price + atr*2,"score":4}
    return None

def strat_inside_bar(df, now_time):
    if len(df) < 3: return None
    last, prev, prev2 = df.iloc[-1], df.iloc[-2], df.iloc[-3]
    was_inside = float(prev["High"]) < float(prev2["High"]) and float(prev["Low"]) > float(prev2["Low"])
    if not was_inside: return None
    price = float(last["Close"])
    if price > float(prev["High"]):
        return {"side":"BUY","price":price,"sl":float(prev["Low"]),"score":5}
    if price < float(prev["Low"]):
        return {"side":"SELL","price":price,"sl":float(prev["High"]),"score":5}
    return None

def strat_stochrsi_st(df, now_time):
    if len(df) < 2: return None
    last, prev = df.iloc[-1], df.iloc[-2]
    price = float(last["Close"]); k, d = float(last["K"]), float(last["D"])
    pk, pd_ = float(prev["K"]), float(prev["D"])
    if pk <= pd_ and k > d and k < 25 and price > float(last["ST_Lower"]):
        return {"side":"BUY","price":price,"sl":float(last["ST_Lower"]),"score":5}
    if pk >= pd_ and k < d and k > 75 and price < float(last["ST_Upper"]):
        return {"side":"SELL","price":price,"sl":float(last["ST_Upper"]),"score":5}
    return None

def strat_momentum_breakout(df, now_time):
    if len(df) < 60: return None
    last = df.iloc[-1]
    price = float(last["Close"])
    high_52 = float(df["High"].iloc[-52:-1].max())
    low_52 = float(df["Low"].iloc[-52:-1].min())
    vr = float(last["Vol_Ratio"])
    if price > high_52 and vr > 1.5: return {"side":"BUY","price":price,"sl":high_52*0.98,"score":7}
    if price < low_52 and vr > 1.5: return {"side":"SELL","price":price,"sl":low_52*1.02,"score":7}
    return None

def strat_volume_spike(df, now_time):
    if len(df) < 25: return None
    last, prev = df.iloc[-1], df.iloc[-2]
    price = float(last["Close"]); vr = float(last["Vol_Ratio"])
    if vr < 2.0: return None
    atr = float(last["ATR"])
    if atr <= 0: return None
    if price > float(prev["High"]) and float(last["Close"]) > float(last["Open"]):
        return {"side":"BUY","price":price,"sl":price - atr*2,"score":6}
    if price < float(prev["Low"]) and float(last["Close"]) < float(last["Open"]):
        return {"side":"SELL","price":price,"sl":price + atr*2,"score":6}
    return None

def strat_keltner_breakout(df, now_time):
    last = df.iloc[-1]; price = float(last["Close"])
    if price > float(last["KC_Upper"]) and float(last["EMA9"]) > float(last["EMA21"]):
        return {"side":"BUY","price":price,"sl":float(last["EMA21"]),"score":5}
    if price < float(last["KC_Lower"]) and float(last["EMA9"]) < float(last["EMA21"]):
        return {"side":"SELL","price":price,"sl":float(last["EMA21"]),"score":5}
    return None

def strat_donchian_breakout(df, now_time):
    last = df.iloc[-1]; price = float(last["Close"])
    if price >= float(last["DC_Upper"]) * 0.999 and float(last["EMA9"]) > float(last["EMA21"]):
        return {"side":"BUY","price":price,"sl":float(last["DC_Lower"]),"score":6}
    if price <= float(last["DC_Lower"]) * 1.001 and float(last["EMA9"]) < float(last["EMA21"]):
        return {"side":"SELL","price":price,"sl":float(last["DC_Upper"]),"score":6}
    return None

def strat_psar_trend(df, now_time):
    last = df.iloc[-1]; price = float(last["Close"]); atr = float(last["ATR"])
    if atr <= 0: return None
    if price > float(last["PSAR"]) and float(last["EMA9"]) > float(last["EMA21"]) and float(last["ADX"]) > 20:
        return {"side":"BUY","price":price,"sl":price - atr*2,"score":4}
    if price < float(last["ST_Upper"]) and float(last["EMA9"]) < float(last["EMA21"]) and float(last["ADX"]) > 20:
        return {"side":"SELL","price":price,"sl":price + atr*2,"score":4}
    return None

def strat_heikin_ashi(df, now_time):
    if len(df) < 3: return None
    last, prev = df.iloc[-1], df.iloc[-2]
    price = float(last["Close"]); atr = float(last["ATR"])
    if atr <= 0: return None
    if bool(last["HA_Bull"]) and bool(prev["HA_Bull"]) and float(last["EMA9"]) > float(last["EMA21"]) and float(last["RSI"]) > 50:
        return {"side":"BUY","price":price,"sl":price - atr*1.5,"score":4}
    if not bool(last["HA_Bull"]) and not bool(prev["HA_Bull"]) and float(last["EMA9"]) < float(last["EMA21"]) and float(last["RSI"]) < 50:
        return {"side":"SELL","price":price,"sl":price + atr*1.5,"score":4}
    return None

def strat_engulfing(df, now_time):
    if len(df) < 2: return None
    last, prev = df.iloc[-1], df.iloc[-2]
    price = float(last["Close"]); atr = float(last["ATR"])
    if atr <= 0: return None
    if float(prev["Close"]) < float(prev["Open"]) and float(last["Close"]) > float(last["Open"]) \
        and float(last["Close"]) > float(prev["Open"]) and float(last["Open"]) < float(prev["Close"]):
        return {"side":"BUY","price":price,"sl":price - atr*1.5,"score":5}
    if float(prev["Close"]) > float(prev["Open"]) and float(last["Close"]) < float(last["Open"]) \
        and float(last["Close"]) < float(prev["Open"]) and float(last["Open"]) > float(prev["Close"]):
        return {"side":"SELL","price":price,"sl":price + atr*1.5,"score":5}
    return None

def strat_hammer_star(df, now_time):
    last = df.iloc[-1]
    o, h, l, c = float(last["Open"]), float(last["High"]), float(last["Low"]), float(last["Close"])
    body = abs(c - o); upper = h - max(o,c); lower = min(o,c) - l
    if body <= 0: return None
    atr = float(last["ATR"])
    if atr <= 0: return None
    if lower > 2*body and upper < body*0.3 and float(last["RSI"]) < 40:
        return {"side":"BUY","price":c,"sl":l - atr*0.5,"score":5}
    if upper > 2*body and lower < body*0.3 and float(last["RSI"]) > 60:
        return {"side":"SELL","price":c,"sl":h + atr*0.5,"score":5}
    return None

def strat_mean_reversion(df, now_time):
    last = df.iloc[-1]
    price = float(last["Close"]); ma = float(last["MA20"]); std = float(last["STD20"])
    if std <= 0: return None
    z = (price - ma) / std
    atr = float(last["ATR"])
    if atr <= 0: return None
    if z < -2 and float(last["RSI"]) < 30:
        return {"side":"BUY","price":price,"sl":price - atr*1.5,"score":4}
    if z > 2 and float(last["RSI"]) > 70:
        return {"side":"SELL","price":price,"sl":price + atr*1.5,"score":4}
    return None

def strat_multi_ema_trend(df, now_time):
    last = df.iloc[-1]
    price = float(last["Close"]); atr = float(last["ATR"])
    if atr <= 0: return None
    e9, e21, e50 = float(last["EMA9"]), float(last["EMA21"]), float(last["EMA50"])
    if e9 > e21 > e50 and price > e9 and float(last["RSI"]) > 55 and float(last["ADX"]) > 20:
        return {"side":"BUY","price":price,"sl":e21 - atr*0.5,"score":6}
    if e9 < e21 < e50 and price < e9 and float(last["RSI"]) < 45 and float(last["ADX"]) > 20:
        return {"side":"SELL","price":price,"sl":e21 + atr*0.5,"score":6}
    return None

STRATEGY_MAP = {
    "ORB": strat_orb, "VWAP_PULLBACK": strat_vwap, "EMA_CROSS": strat_ema_cross,
    "SUPERTREND_ADX": strat_supertrend_adx, "BB_SQUEEZE": strat_bb_squeeze,
    "RSI_DIVERGENCE": strat_rsi_divergence, "CPR": strat_cpr, "MACD_RSI": strat_macd_rsi,
    "INSIDE_BAR": strat_inside_bar, "STOCHRSI_ST": strat_stochrsi_st,
    "MOMENTUM_BREAKOUT": strat_momentum_breakout, "VOLUME_SPIKE": strat_volume_spike,
    "KELTNER_BREAKOUT": strat_keltner_breakout, "DONCHIAN_BREAKOUT": strat_donchian_breakout,
    "PSAR_TREND": strat_psar_trend, "HEIKIN_ASHI": strat_heikin_ashi,
    "ENGULFING": strat_engulfing, "HAMMER_STAR": strat_hammer_star,
    "MEAN_REVERSION": strat_mean_reversion, "MULTI_EMA_TREND": strat_multi_ema_trend,
}

# ============================================================
# ==================== SIGNAL AGGREGATION ====================
# ============================================================
def get_combined_signal(df, now_time, disabled, stats):
    signals = {"BUY": [], "SELL": []}
    for strat_name in STRATEGY_NAMES:
        if strat_name in disabled: continue
        s = stats.get(strat_name, {})
        if s.get("streak_losses", 0) >= AUTO_DISABLE_AFTER_LOSSES: continue
        if s.get("total", 0) >= 20 and s.get("wins", 0)/max(1, s.get("total", 1)) < STRATEGY_MIN_WINRATE: continue
        try:
            sig = STRATEGY_MAP[strat_name](df, now_time)
            if sig and sig.get("price", 0) > 0:
                signals[sig["side"]].append({
                    "name": strat_name, "price": sig["price"],
                    "sl": sig["sl"], "score": sig["score"]
                })
        except Exception as e:
            print(f"[{strat_name}] {e}")
            continue

    buy_score = sum(s["score"] for s in signals["BUY"])
    sell_score = sum(s["score"] for s in signals["SELL"])

    if buy_score >= MIN_SIGNAL_SCORE and buy_score > sell_score:
        sl = max(s["sl"] for s in signals["BUY"])
        return {"side":"BUY","price":signals["BUY"][0]["price"],"sl":sl,
                "score":buy_score,"strategies":[s["name"] for s in signals["BUY"]]}
    if sell_score >= MIN_SIGNAL_SCORE and sell_score > buy_score:
        sl = min(s["sl"] for s in signals["SELL"])
        return {"side":"SELL","price":signals["SELL"][0]["price"],"sl":sl,
                "score":sell_score,"strategies":[s["name"] for s in signals["SELL"]]}
    return None

# ============================================================
# ==================== POSITION SIZING =======================
# ============================================================
def calc_position_size(available_capital, price, sl, atr):
    risk_per_share = abs(price - sl)
    if risk_per_share <= 0: return 0
    risk_amount = available_capital * RISK_PER_TRADE_PCT
    if atr > 0:
        atr_pct = atr / price
        if atr_pct > 0.03: risk_amount *= 0.5
        elif atr_pct > 0.02: risk_amount *= 0.75
    qty = int(risk_amount / risk_per_share)
    max_cost = available_capital * 0.25
    if qty * price > max_cost: qty = int(max_cost // price)
    if qty * price > available_capital: qty = int(available_capital // price)
    return max(0, qty)

def count_open_positions(state): return len(state.get("open_positions", []))

# ============================================================
# ==================== SCAN (FIXED - no manage, multi-entry)
# ============================================================
def run_scan(state, stats):
    """FIX: Takes state and stats as params, no manage call, multi-entry"""
    now = datetime.now(IST)
    today = str(now.date())

    if state["loss_today"] >= DAILY_LOSS_LIMIT_PCT * state["starting_capital"]: return
    if state["trades_today"] >= MAX_TRADES_PER_DAY: return

    # FIX: Fill up to MAX_POSITIONS slots
    slots = MAX_POSITIONS - count_open_positions(state)
    if slots <= 0: return

    now_time = now.time()
    candidates = []
    seen_syms = set()

    for sym in WATCHLIST:
        if any(p["symbol"] == sym for p in state.get("open_positions", [])): continue
        if sym in seen_syms: continue
        df = fetch_daily(sym)
        if df is None: continue
        try: df = add_indicators(df)
        except: continue
        sig = get_combined_signal(df, now_time, state["disabled_today"], stats)
        if not sig: continue

        last = df.iloc[-1]
        atr = float(last["ATR"])
        price = sig["price"]; sl = sig["sl"]
        if atr <= 0: continue
        if sig["side"] == "BUY" and sl >= price: continue
        if sig["side"] == "SELL" and sl <= price: continue

        qty = calc_position_size(state["capital"], price, sl, atr)
        if qty < 1: continue
        cost = price * qty
        if cost > state["capital"]: continue

        rps = abs(price - sl)
        if sig["side"] == "BUY":
            t1 = price + TARGET_1_R_MULTIPLE * rps
            t2 = price + TARGET_2_R_MULTIPLE * rps
        else:
            t1 = price - TARGET_1_R_MULTIPLE * rps
            t2 = price - TARGET_2_R_MULTIPLE * rps

        est_c = calc_charges(price, t2, qty)
        est_net = rps * TARGET_2_R_MULTIPLE * qty - est_c
        if est_net < min_required_net_profit(): continue

        candidates.append({
            "symbol": sym, "price": price, "sl": sl, "qty": qty,
            "cost": cost, "score": sig["score"], "strategies": sig["strategies"],
            "side": sig["side"], "target_1r": t1, "target_2r": t2,
            "est_charges": est_c, "est_net": est_net
        })
        seen_syms.add(sym)

    if not candidates: return
    candidates.sort(key=lambda x: x["score"], reverse=True)

    # FIX: Take top candidates up to available slots
    entries_taken = 0
    for best in candidates:
        if entries_taken >= slots: break
        if state["trades_today"] + entries_taken >= MAX_TRADES_PER_DAY: break

        cost = best["cost"]
        # FIX: recompute available
        if cost > state["capital"]: continue

        new_pos = {
            "symbol": best["symbol"], "entry": best["price"], "qty": best["qty"],
            "sl": best["sl"], "initial_sl": best["sl"], "trail_high": best["price"],
            "target_1r": best["target_1r"], "target_2r": best["target_2r"],
            "side": best["side"], "strategies": best["strategies"],
            "entry_time": str(now), "entry_date": today,
            "entry_dt": now.isoformat(), "days_held": 0, "partial_booked": False
        }
        state["open_positions"].append(new_pos)
        state["capital"] -= cost  # FIX: deduct after each entry
        entries_taken += 1

        sl_pct = abs(best["price"] - best["sl"]) / best["price"] * 100
        send_telegram(
            f"📈 *PAPER {best['side']} — QUICK ENTRY*\n"
            f"Stock: {best['symbol']}\n"
            f"Price: ₹{best['price']:.2f}\n"
            f"Qty: {best['qty']}\n"
            f"Cost: ₹{best['cost']:.2f}\n"
            f"Stop Loss: ₹{best['sl']:.2f} ({sl_pct:.2f}%)\n"
            f"Target 1R (60% book): ₹{best['target_1r']:.2f}\n"
            f"Target 2R (final): ₹{best['target_2r']:.2f}\n"
            f"Signal Score: {best['score']}\n"
            f"Strategies: {', '.join(best['strategies'])}\n"
            f"Est. Charges: ₹{best['est_charges']:.2f}\n"
            f"Est. Net: ₹{best['est_net']:.2f}\n"
            f"Positions: {count_open_positions(state)}/{MAX_POSITIONS}\n"
            f"Available Cash: ₹{state['capital']:.2f}"
        )

    if entries_taken > 0:
        save_state(state)

# ============================================================
# ==================== MANAGE POSITION (FIXED) ==============
# ============================================================
def manage_open_position(state, stats, pos):
    sym = pos["symbol"]
    df = fetch_intraday(sym)
    if df is None or len(df) == 0: return
    try:
        price = float(df["Close"].iloc[-1])
    except: return

    side = pos["side"]

    # Days held
    try:
        entry_date = datetime.strptime(pos.get("entry_date", str(datetime.now(IST).date())), "%Y-%m-%d").date()
    except:
        entry_date = datetime.now(IST).date()
    today = datetime.now(IST).date()
    pos["days_held"] = (today - entry_date).days

    # Hours held (FIX: safe parse with entry_time fallback)
    entry_dt = safe_parse_dt(pos.get("entry_dt"))
    if entry_dt is None:
        entry_dt = safe_parse_dt(pos.get("entry_time"))
    if entry_dt is None:
        hours_held = 0
    else:
        if entry_dt.tzinfo is None:
            entry_dt = IST.localize(entry_dt)
        hours_held = (datetime.now(IST) - entry_dt).total_seconds() / 3600

    rps = abs(pos["entry"] - pos["initial_sl"])
    if rps <= 0: return

    if side == "BUY":
        if price > pos["trail_high"]: pos["trail_high"] = price
    else:
        if price < pos["trail_high"]: pos["trail_high"] = price

    # Partial book — FIX: skip if qty < 2
    if not pos.get("partial_booked") and pos["qty"] >= 2:
        hit_1r = (side == "BUY" and price >= pos["target_1r"]) or (side == "SELL" and price <= pos["target_1r"])
        if hit_1r:
            book_qty = int(pos["qty"] * PARTIAL_BOOK_PCT)
            if book_qty < 1: book_qty = 1
            if book_qty >= pos["qty"]: book_qty = pos["qty"] - 1
            if book_qty >= 1:
                if side == "BUY":
                    gross = (price - pos["entry"]) * book_qty
                else:
                    gross = (pos["entry"] - price) * book_qty
                charges = calc_charges(pos["entry"], price, book_qty)
                net = gross - charges
                proceeds = pos["entry"] * book_qty + net
                state["capital"] += proceeds
                pos["qty"] -= book_qty
                pos["partial_booked"] = True
                pos["sl"] = pos["entry"]
                log_trade({
                    "date": str(today), "time": str(datetime.now(IST).time()),
                    "symbol": sym, "strategy": "PARTIAL_1R", "side": side,
                    "entry": pos["entry"], "qty": book_qty, "exit": price,
                    "gross": round(gross, 2), "charges": charges,
                    "net": round(net, 2), "reason": "Partial 1R quick book",
                    "capital_after": round(state["capital"], 2), "mode": CAPITAL_MODE
                })
                save_state(state)
                send_telegram(
                    f"💰 *QUICK BOOK 60% at 1R*\n"
                    f"Stock: {sym}\n"
                    f"Booked: {book_qty} shares\n"
                    f"Price: ₹{price:.2f}\n"
                    f"Net Profit: ₹{net:.2f}\n"
                    f"SL → Breakeven: ₹{pos['entry']:.2f}\n"
                    f"Remaining: {pos['qty']} shares"
                )

    # Trailing SL
    if pos.get("partial_booked"):
        if side == "BUY":
            new_sl = max(pos["sl"], price * (1 - TRAIL_PCT_AFTER_1R))
            if new_sl > pos["sl"]: pos["sl"] = new_sl; save_state(state)
        else:
            new_sl = min(pos["sl"], price * (1 + TRAIL_PCT_AFTER_1R))
            if new_sl < pos["sl"]: pos["sl"] = new_sl; save_state(state)
    else:
        if side == "BUY":
            new_sl = max(pos["sl"], price * (1 - TRAIL_PCT_BEFORE_1R))
            if new_sl > pos["sl"]: pos["sl"] = new_sl; save_state(state)
        else:
            new_sl = min(pos["sl"], price * (1 + TRAIL_PCT_BEFORE_1R))
            if new_sl < pos["sl"]: pos["sl"] = new_sl; save_state(state)

    # Momentum boost trail lock (FIX: save_state added)
    if side == "BUY":
        move_r = (price - pos["entry"]) / rps
    else:
        move_r = (pos["entry"] - price) / rps
    if move_r >= MOMENTUM_BOOST_R:
        if side == "BUY":
            lock_sl = price * (1 - 0.005)
            if lock_sl > pos["sl"]:
                pos["sl"] = lock_sl
                save_state(state)  # FIX
        else:
            lock_sl = price * (1 + 0.005)
            if lock_sl < pos["sl"]:
                pos["sl"] = lock_sl
                save_state(state)  # FIX

    # Exit checks
    exit_price, reason = None, None
    if side == "BUY":
        if price <= pos["sl"]: exit_price, reason = price, "SL hit"
        elif price >= pos["target_2r"]: exit_price, reason = price, "2R target"
    else:
        if price >= pos["sl"]: exit_price, reason = price, "SL hit"
        elif price <= pos["target_2r"]: exit_price, reason = price, "2R target"

    # No-move exit
    if not exit_price and hours_held >= NO_MOVE_EXIT_HOURS and move_r < 0.5:
        exit_price, reason = price, f"No-move exit ({int(hours_held)}h)"

    # Max days exit
    if not exit_price and pos["days_held"] >= HOLD_DAYS_MAX:
        if (side == "BUY" and price > pos["entry"]) or (side == "SELL" and price < pos["entry"]):
            exit_price, reason = price, f"Time exit ({HOLD_DAYS_MAX}d, profit)"
        else:
            exit_price, reason = price, f"Time exit ({HOLD_DAYS_MAX}d)"

    if not exit_price: return

    # Close
    if side == "BUY":
        gross = (exit_price - pos["entry"]) * pos["qty"]
    else:
        gross = (pos["entry"] - exit_price) * pos["qty"]
    charges = calc_charges(pos["entry"], exit_price, pos["qty"])
    net = gross - charges
    proceeds = pos["entry"] * pos["qty"] + net

    state["capital"] += proceeds
    state["trades_today"] += 1
    if net < 0: state["loss_today"] += abs(net)

    for sname in pos["strategies"]:
        if sname in stats:
            if net > 0:
                stats[sname]["wins"] += 1; stats[sname]["streak_losses"] = 0
            else:
                stats[sname]["losses"] += 1; stats[sname]["streak_losses"] += 1
            stats[sname]["pnl"] = round(stats[sname]["pnl"] + net, 2)
            stats[sname]["total"] = stats[sname]["wins"] + stats[sname]["losses"]
    save_strategy_stats(stats)

    log_trade({
        "date": str(today), "time": str(datetime.now(IST).time()),
        "symbol": sym, "strategy": "|".join(pos["strategies"]), "side": side,
        "entry": pos["entry"], "qty": pos["qty"], "exit": exit_price,
        "gross": round(gross, 2), "charges": charges,
        "net": round(net, 2), "reason": reason,
        "capital_after": round(state["capital"], 2), "mode": CAPITAL_MODE
    })

    emoji = "✅" if net > 0 else "❌"
    send_telegram(
        f"{emoji} *PAPER {side} EXIT*\n"
        f"Stock: {sym}\n"
        f"Entry: ₹{pos['entry']:.2f}\n"
        f"Exit: ₹{exit_price:.2f}\n"
        f"Qty: {pos['qty']}\n"
        f"Held: {pos['days_held']}d / {int(hours_held)}h\n"
        f"Reason: {reason}\n"
        f"Gross: ₹{gross:.2f}\n"
        f"Charges: ₹{charges:.2f}\n"
        f"Net: ₹{net:.2f}\n"
        f"Available: ₹{state['capital']:.2f}"
    )

    state["open_positions"].remove(pos)
    save_state(state)

# ============================================================
# ==================== SUMMARIES =============================
# ============================================================
def generate_summary(period):
    if not os.path.exists(LOG_FILE): return None
    try: df = pd.read_csv(LOG_FILE)
    except: return None
    if len(df) == 0: return None
    df["date"] = pd.to_datetime(df["date"])
    today = datetime.now(IST).date()

    if period == "daily":
        mask = df["date"].dt.date == today; title = "📊 Daily Summary"
    elif period == "weekly":
        mask = df["date"].dt.date >= (today - timedelta(days=7)); title = "📊 Weekly Summary"
    else:
        mask = df["date"].dt.date >= (today - timedelta(days=30)); title = "📊 Monthly Summary"

    sub = df[mask]
    if len(sub) == 0: return None

    total = len(sub); wins = len(sub[sub["net"] > 0]); losses = len(sub[sub["net"] <= 0])
    winrate = (wins / total * 100) if total else 0
    gross = sub["gross"].sum(); charges = sub["charges"].sum(); net = sub["net"].sum()
    avg_win = sub[sub["net"] > 0]["net"].mean() if wins > 0 else 0
    avg_loss = sub[sub["net"] <= 0]["net"].mean() if losses > 0 else 0

    msg = f"*{title}*\n"
    msg += f"Trades: {total} | Wins: {wins} | Losses: {losses}\n"
    msg += f"Win Rate: {winrate:.1f}%\n"
    msg += f"Avg Win: ₹{avg_win:.2f} | Avg Loss: ₹{avg_loss:.2f}\n"
    msg += f"Gross: ₹{gross:.2f} | Charges: ₹{charges:.2f}\n"
    msg += f"*Net P&L: ₹{net:.2f}*\n\n"

    msg += "*Strategy Performance:*\n"
    strat_df = sub[sub["strategy"] != "PARTIAL_1R"]
    for s in STRATEGY_NAMES:
        ssub = strat_df[strat_df["strategy"].str.contains(s, na=False)]
        if len(ssub) == 0: continue
        sw = len(ssub[ssub["net"] > 0]); sl_ = len(ssub[ssub["net"] <= 0])
        msg += f"• {s}: {len(ssub)}T ({sw}W/{sl_}L) ₹{ssub['net'].sum():.2f}\n"

    fname = f"trades_{period}_{today}.csv"
    sub.to_csv(fname, index=False)
    return msg, fname

def check_summaries(state):
    now = datetime.now(IST); today = str(now.date()); updated = False

    if now.time() >= dtime(15, 35) and state.get("last_daily") != today:
        r = generate_summary("daily")
        if r:
            send_telegram(r[0]); send_document(r[1], "Daily log")
        state["last_daily"] = today; updated = True

    if now.weekday() == 5 and now.time() >= dtime(10, 0):
        wk = f"{now.year}-W{now.isocalendar()[1]}"
        if state.get("last_weekly") != wk:
            r = generate_summary("weekly")
            if r:
                send_telegram(r[0]); send_document(r[1], "Weekly log")
            state["last_weekly"] = wk; updated = True

    if now.day == 1 and now.time() >= dtime(10, 0):
        mk = f"{now.year}-{now.month}"
        if state.get("last_monthly") != mk:
            r = generate_summary("monthly")
            if r:
                send_telegram(r[0]); send_document(r[1], "Monthly log")
            state["last_monthly"] = mk; updated = True

    if updated: save_state(state)

# ============================================================
# ==================== MAIN LOOP (FIXED) =====================
# ============================================================
if __name__ == "__main__":
    send_telegram(
        f"🤖 *Paper Trading Bot v7.3 ONLINE*\n\n"
        f"Mode: *DELIVERY QUICK PROFIT*\n"
        f"Capital: ₹{CAPITAL_START}\n"
        f"Risk/Trade: {RISK_PER_TRADE_PCT*100}%\n"
        f"Max Positions: {MAX_POSITIONS}\n"
        f"Max Hold: {HOLD_DAYS_MAX} days\n"
        f"Partial: 60% at 1R | Final: 2R\n"
        f"Tight Trail: 0.8%\n"
        f"No-Move Exit: {NO_MOVE_EXIT_HOURS}h\n"
        f"Strategies: {len(STRATEGY_NAMES)}\n"
        f"Universe: {len(WATCHLIST)} stocks"
    )

    while True:
        try:
            now = datetime.now(IST)
            state = load_state()
            stats = load_strategy_stats()

            # FIX: Daily reset first (before any manage/scan)
            daily_reset_if_needed(state)

            # Update peak capital
            if state["capital"] > state["peak_capital"]:
                state["peak_capital"] = state["capital"]
                save_state(state)

            # Drawdown check
            dd = (state["peak_capital"] - state["capital"]) / max(1, state["peak_capital"])
            if dd >= MAX_DRAWDOWN_PCT:
                today = str(now.date())
                if state.get("drawdown_alerted") != today:
                    send_telegram(f"🛑 *HALTED*\nDrawdown: {dd*100:.1f}%")
                    state["drawdown_alerted"] = today
                    save_state(state)

            # FIX: Manage positions ONCE (only in main loop)
            if dtime(9, 15) <= now.time() <= dtime(15, 30) and now.weekday() < 5:
                if dd < MAX_DRAWDOWN_PCT:
                    for pos in list(state.get("open_positions", [])):
                        try: manage_open_position(state, stats, pos)
                        except Exception as e: print(f"[manage {pos.get('symbol')}] {e}")

            # FIX: Scan only — no manage inside
            if dtime(9, 30) <= now.time() <= dtime(15, 0) and now.weekday() < 5:
                if dd < MAX_DRAWDOWN_PCT:
                    try: run_scan(state, stats)
                    except Exception as e: print(f"[scan] {e}")

            check_summaries(state)
            time.sleep(900)
        except KeyboardInterrupt: break
        except Exception as e:
            send_telegram(f"⚠️ *Error*\n{str(e)[:200]}")
            time.sleep(60)
