import yfinance as yf, pandas as pd, numpy as np, time, json, os, requests, pytz
from datetime import datetime, time as dtime, timedelta
import warnings; warnings.filterwarnings('ignore')

TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
CAP = 5000.0; MODE = "DELIVERY"; RISK = 0.015; DLL = 0.03; MDD = 0.12
MAXPOS = 3; MAXTD = 4; MINS = 5
T1M = 1.0; T2M = 2.0; PB = 0.6; TRAIL1 = 0.008; TRAIL0 = 0.012
HOLD = 3; NOMOVE = 36; BOOST = 1.5
STT = 0.001; EXCH = 0.0000322; SEBI = 0.000001; STAMP = 0.00015; DP = 13.5; GST = 0.18
MPM = 3; ADL = 3; SWR = 0.35

NSE = ["RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS","SBIN.NS","ITC.NS","LT.NS","AXISBANK.NS","KOTAKBANK.NS","BHARTIARTL.NS","HINDUNILVR.NS","MARUTI.NS","ASIANPAINT.NS","TITAN.NS","BAJFINANCE.NS","HCLTECH.NS","WIPRO.NS","TECHM.NS","SUNPHARMA.NS","TATAMOTORS.NS","TATASTEEL.NS","JSWSTEEL.NS","POWERGRID.NS","NTPC.NS","ONGC.NS","COALINDIA.NS","DRREDDY.NS","CIPLA.NS","ULTRACEMCO.NS","ADANIENT.NS","ADANIPORTS.NS","BAJAJFINSV.NS","BAJAJ-AUTO.NS","GRASIM.NS","HEROMOTOCO.NS","HINDALCO.NS","INDUSINDBK.NS","M&M.NS","NESTLEIND.NS","SHREECEM.NS","TATACONSUM.NS","DIVISLAB.NS","BRITANNIA.NS","EICHERMOT.NS","APOLLOHOSP.NS","BPCL.NS","IOC.NS","PIDILITIND.NS","DABUR.NS","GODREJCP.NS","MARICO.NS","BERGEPAINT.NS","HAVELLS.NS","SIEMENS.NS","DMART.NS","BAJAJHLDNG.NS","AMBUJACEM.NS","BANKBARODA.NS","PNB.NS","CANBK.NS","IDFCFIRSTB.NS","FEDERALBNK.NS","BANDHANBNK.NS","RBLBANK.NS","AUBANK.NS","INDIGO.NS","TRENT.NS","VEDL.NS","GAIL.NS","MOTHERSON.NS","BOSCHLTD.NS","ABBOTINDIA.NS","PGHH.NS","COLPAL.NS","UBL.NS","JUBLFOOD.NS","PAGEIND.NS","LICI.NS","IRCTC.NS","ZOMATO.NS","NYKAA.NS","PAYTM.NS","POLICYBZR.NS","DELHIVERY.NS","CAMS.NS","KPITTECH.NS","PERSISTENT.NS","LTIM.NS","MPHASIS.NS","COFORGE.NS","TATAELXSI.NS","LTTS.NS","BEL.NS","HAL.NS","BHEL.NS","CONCOR.NS","RECLTD.NS","PFC.NS","IRFC.NS","RVNL.NS","IRCON.NS","NBCC.NS"]
BSE = ["RELIANCE.BO","TCS.BO","HDFCBANK.BO","INFY.BO","ICICIBANK.BO","SBIN.BO","ITC.BO","LT.BO","AXISBANK.BO","KOTAKBANK.BO","BHARTIARTL.BO","HINDUNILVR.BO","MARUTI.BO","ASIANPAINT.BO","TITAN.BO","BAJFINANCE.BO","HCLTECH.BO","WIPRO.BO","SUNPHARMA.BO","TATAMOTORS.BO","TATASTEEL.BO","POWERGRID.BO","NTPC.BO","ONGC.BO","COALINDIA.BO","DRREDDY.BO","CIPLA.BO","ULTRACEMCO.BO","ADANIENT.BO","ADANIPORTS.BO","GRASIM.BO","HEROMOTOCO.BO","HINDALCO.BO","INDUSINDBK.BO","M&M.BO","NESTLEIND.BO","SHREECEM.BO","TATACONSUM.BO","BRITANNIA.BO","EICHERMOT.BO","APOLLOHOSP.BO","BPCL.BO","IOC.BO","PIDILITIND.BO","DABUR.BO","GODREJCP.BO","MARICO.BO","HAVELLS.BO","SIEMENS.BO","DMART.BO","BANKBARODA.BO","PNB.BO","CANBK.BO","GAIL.BO","VEDL.BO","BEL.BO","HAL.BO","BHEL.BO"]
def uni():
    s=set();c=[]
    for x in NSE:
        b=x.replace(".NS","")
        if b not in s: s.add(b);c.append(x)
    for x in BSE:
        b=x.replace(".BO","")
        if b not in s: s.add(b);c.append(x)
    return c
WL = uni()
SN = ["ORB","VWAP","EMA","STADX","BBSQ","RSID","CPR","MACD","IB","SRSI","MOM","VOL","KELT","DON","PSAR","HA","ENG","HAM","MR","MEM"]
IST = pytz.timezone("Asia/Kolkata")
CF="capital.json"; LF="trades.csv"; SF="stats.json"

def tg(m):
    if not TOKEN or not CHAT_ID: print("[TG] missing"); return
    try:
        r=requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage",params={"chat_id":CHAT_ID,"text":m,"parse_mode":"Markdown"},timeout=10)
        if r.status_code!=200: print(f"[TG] {r.status_code}")
    except Exception as e: print(f"[TG] {e}")

def tgd(f,c=""):
    if not TOKEN or not CHAT_ID or not os.path.exists(f): return
    try:
        with open(f,"rb") as x: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendDocument",data={"chat_id":CHAT_ID,"caption":c},files={"document":x},timeout=30)
    except Exception as e: print(f"[Doc] {e}")

def chg(bp,sp,q):
    bv=bp*q; sv=sp*q; t=bv+sv
    return round(STT*(bv+sv)+EXCH*t+SEBI*t+STAMP*bv+DP+GST*(EXCH*t+SEBI*t),2)

def minp():
    return max(12.0, chg(500,505,5)*MPM)

def ls():
    d={"capital":CAP,"starting_capital":CAP,"peak_capital":CAP,"date":str(datetime.now(IST).date()),"trades_today":0,"loss_today":0.0,"open_positions":[],"disabled_today":[],"last_daily":"","last_weekly":"","last_monthly":"","drawdown_alerted":""}
    if os.path.exists(CF):
        try:
            with open(CF) as f: s=json.load(f)
            for k,v in d.items(): s.setdefault(k,v)
            if not isinstance(s.get("open_positions"),list): s["open_positions"]=[]
            if not isinstance(s.get("disabled_today"),list): s["disabled_today"]=[]
            return s
        except: return d.copy()
    return d.copy()

def ss(s):
    try:
        s["open_positions"]=list(s.get("open_positions",[]))
        s["disabled_today"]=list(s.get("disabled_today",[]))
        with open(CF,"w") as f: json.dump(s,f,indent=2,default=str)
    except Exception as e: print(f"[Save] {e}")

def drs(s):
    t=str(datetime.now(IST).date())
    if s["date"]!=t:
        s["date"]=t; s["trades_today"]=0; s["loss_today"]=0.0; s["disabled_today"]=[]; s["drawdown_alerted"]=""; ss(s)
        return True,t
    return False,t

def lstats():
    st={}
    if os.path.exists(SF):
        try:
            with open(SF) as f: st=json.load(f)
        except: st={}
    for s in SN:
        if s not in st or not isinstance(st.get(s),dict): st[s]={"wins":0,"losses":0,"pnl":0.0,"streak_losses":0,"total":0}
        else:
            st[s].setdefault("wins",0); st[s].setdefault("losses",0); st[s].setdefault("pnl",0.0); st[s].setdefault("streak_losses",0); st[s].setdefault("total",0)
    return st

def sstats(st):
    try:
        with open(SF,"w") as f: json.dump(st,f,indent=2)
    except Exception as e: print(f"[Stats] {e}")

def lt(r):
    try:
        d=pd.DataFrame([r])
        if os.path.exists(LF): d.to_csv(LF,mode="a",header=False,index=False)
        else: d.to_csv(LF,index=False)
    except Exception as e: print(f"[Log] {e}")

def pdt(s):
    if not s: return None
    try: return datetime.fromisoformat(s)
    except:
        try: return datetime.strptime(s,"%Y-%m-%d %H:%M:%S.%f%z")
        except:
            try: return datetime.strptime(s,"%Y-%m-%d %H:%M:%S.%f")
            except: return None

def fl(df):
    if df is None: return None
    if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df

def fd(s):
    try:
        df=fl(yf.download(s,period="90d",interval="1d",progress=False,auto_adjust=True))
        if df is None or len(df)<50: return None
        return df
    except: return None

def fi(s):
    try:
        df=fl(yf.download(s,period="5d",interval="15m",progress=False,auto_adjust=True))
        if df is None or len(df)<5: return None
        return df
    except: return None

def ind(df):
    df["E9"]=df["Close"].ewm(span=9).mean(); df["E21"]=df["Close"].ewm(span=21).mean()
    df["E50"]=df["Close"].ewm(span=50).mean()
    d=df["Close"].diff(); g=d.clip(lower=0).rolling(14).mean(); l=-d.clip(upper=0).rolling(14).mean()
    df["RSI"]=(100-(100/(1+g/l.replace(0,np.nan)))).fillna(50)
    df["TR"]=df[["High","Low","Close"]].apply(lambda x:max(x["High"]-x["Low"],abs(x["High"]-x["Close"]),abs(x["Low"]-x["Close"])),axis=1)
    df["ATR"]=df["TR"].rolling(14).mean().fillna(df["TR"].rolling(5).mean()).fillna(0)
    pdm=df["High"].diff().clip(lower=0); ndm=(-df["Low"].diff()).clip(lower=0)
    t14=df["TR"].rolling(14).sum().replace(0,np.nan)
    pdi=100*(pdm.rolling(14).sum()/t14); ndi=100*(ndm.rolling(14).sum()/t14)
    dx=100*abs(pdi-ndi)/(pdi+ndi).replace(0,np.nan)
    df["ADX"]=dx.rolling(14).mean().fillna(0); df["PDI"]=pdi.fillna(0); df["NDI"]=ndi.fillna(0)
    tp=(df["High"]+df["Low"]+df["Close"])/3
    df["VWAP"]=((tp*df["Volume"]).cumsum()/df["Volume"].cumsum().replace(0,np.nan)).fillna(df["Close"])
    df["M20"]=df["Close"].rolling(20).mean(); df["S20"]=df["Close"].rolling(20).std().fillna(0)
    df["BBU"]=df["M20"]+2*df["S20"]; df["BBL"]=df["M20"]-2*df["S20"]
    df["BBW"]=(df["BBU"]-df["BBL"])/df["M20"]; df["BBW20"]=df["BBW"].rolling(20).mean()
    df["STU"]=(df["High"]+df["Low"])/2+3*df["ATR"]; df["STL"]=(df["High"]+df["Low"])/2-3*df["ATR"]
    e12=df["Close"].ewm(span=12).mean(); e26=df["Close"].ewm(span=26).mean()
    df["MACD"]=e12-e26; df["MACDS"]=df["MACD"].ewm(span=9).mean()
    rmn=df["RSI"].rolling(14).min(); rmx=df["RSI"].rolling(14).max()
    df["SR"]=(df["RSI"]-rmn)/(rmx-rmn+0.0001)*100; df["K"]=df["SR"].rolling(3).mean(); df["D"]=df["K"].rolling(3).mean()
    df["KCU"]=df["E21"]+2*df["ATR"]; df["KCL"]=df["E21"]-2*df["ATR"]
    df["DCU"]=df["High"].rolling(20).max(); df["DCL"]=df["Low"].rolling(20).min()
    df["PSAR"]=df["Low"].rolling(5).min()
    df["VM20"]=df["Volume"].rolling(20).mean().replace(0,np.nan)
    df["VR"]=(df["Volume"]/df["VM20"]).fillna(1.0)
    df["HC"]=(df["Open"]+df["High"]+df["Low"]+df["Close"])/4; df["HO"]=(df["Open"].shift(1)+df["Close"].shift(1))/2
    df["HB"]=df["HC"]>df["HO"]
    return df

def s_orb(df,t):
    if len(df)<2: return None
    try:
        L,P=df.iloc[-1],df.iloc[-2]; a=float(L["ATR"]); p=float(L["Close"]); h=float(P["High"]); lo=float(P["Low"])
        if a<=0: return None
        if p>h*1.005: return{"s":"BUY","p":p,"sl":max(lo,p-a*2),"sc":6}
        if p<lo*0.995: return{"s":"SELL","p":p,"sl":min(h,p+a*2),"sc":6}
    except: pass
    return None

def s_vwap(df,t):
    if len(df)<2: return None
    L,P=df.iloc[-1],df.iloc[-2]; p=float(L["Close"]); v=float(L["VWAP"]); a=float(L["ATR"])
    if a<=0: return None
    if float(P["Close"])<float(P["VWAP"]) and p>v*1.002: return{"s":"BUY","p":p,"sl":p-a*2,"sc":5}
    if float(P["Close"])>float(P["VWAP"]) and p<v*0.998: return{"s":"SELL","p":p,"sl":p+a*2,"sc":5}
    return None

def s_ema(df,t):
    if len(df)<2: return None
    L,P=df.iloc[-1],df.iloc[-2]; p=float(L["Close"]); r=float(L["RSI"]); a=float(L["ATR"])
    if a<=0: return None
    if float(P["E9"])<=float(P["E21"]) and float(L["E9"])>float(L["E21"]) and 50<r<72: return{"s":"BUY","p":p,"sl":p-a*2,"sc":5}
    if float(P["E9"])>=float(P["E21"]) and float(L["E9"])<float(L["E21"]) and 28<r<50: return{"s":"SELL","p":p,"sl":p+a*2,"sc":5}
    return None

def s_stadx(df,t):
    L=df.iloc[-1]; p=float(L["Close"]); a=float(L["ADX"])
    if a<25: return None
    if p>float(L["STL"]) and float(L["E9"])>float(L["E21"]) and float(L["PDI"])>float(L["NDI"]): return{"s":"BUY","p":p,"sl":float(L["STL"]),"sc":6}
    if p<float(L["STU"]) and float(L["E9"])<float(L["E21"]) and float(L["NDI"])>float(L["PDI"]): return{"s":"SELL","p":p,"sl":float(L["STU"]),"sc":6}
    return None

def s_bbsq(df,t):
    L=df.iloc[-1]; p=float(L["Close"])
    if float(L["ADX"])>20: return None
    w=float(L["BBW"]); w20=float(L["BBW20"])
    if pd.isna(w) or pd.isna(w20) or w>=w20: return None
    if p>float(L["BBU"]): return{"s":"BUY","p":p,"sl":float(L["M20"]),"sc":5}
    if p<float(L["BBL"]): return{"s":"SELL","p":p,"sl":float(L["M20"]),"sc":5}
    return None

def s_rsid(df,t):
    if len(df)<30: return None
    L=df.iloc[-1]; p=float(L["Close"]); lb=10
    pl=float(df["Low"].iloc[-lb:-1].min()); ph=float(df["High"].iloc[-lb:-1].max())
    prl=float(df["RSI"].iloc[-lb:-1].min()); prh=float(df["RSI"].iloc[-lb:-1].max())
    r=float(L["RSI"]); a=float(L["ATR"])
    if a<=0: return None
    if float(L["Low"])<pl and r>prl+3: return{"s":"BUY","p":p,"sl":p-a*1.5,"sc":5}
    if float(L["High"])>ph and r<prh-3: return{"s":"SELL","p":p,"sl":p+a*1.5,"sc":5}
    return None

def s_cpr(df,t):
    if len(df)<2: return None
    P=df.iloc[-2]; ph=float(P["High"]); pl=float(P["Low"]); pc=float(P["Close"])
    piv=(ph+pl+pc)/3; bc=(ph+pl)/2; tc=(piv-bc)+piv
    L=df.iloc[-1]; p=float(L["Close"]); a=float(L["ATR"])
    if a<=0: return None
    if abs(tc-bc)>0.002*p: return None
    if p>max(tc,bc) and float(L["Close"])>float(L["Open"]): return{"s":"BUY","p":p,"sl":min(piv,p-a*2),"sc":5}
    if p<min(tc,bc) and float(L["Close"])<float(L["Open"]): return{"s":"SELL","p":p,"sl":max(piv,p+a*2),"sc":5}
    return None

def s_macd(df,t):
    if len(df)<2: return None
    L,P=df.iloc[-1],df.iloc[-2]; p=float(L["Close"]); r=float(L["RSI"]); a=float(L["ATR"])
    if a<=0: return None
    u=float(P["MACD"])<=float(P["MACDS"]) and float(L["MACD"])>float(L["MACDS"])
    d=float(P["MACD"])>=float(P["MACDS"]) and float(L["MACD"])<float(L["MACDS"])
    if u and 50<r<72: return{"s":"BUY","p":p,"sl":p-a*2,"sc":4}
    if d and 28<r<50: return{"s":"SELL","p":p,"sl":p+a*2,"sc":4}
    return None

def s_ib(df,t):
    if len(df)<3: return None
    L,P,P2=df.iloc[-1],df.iloc[-2],df.iloc[-3]
    if not(float(P["High"])<float(P2["High"]) and float(P["Low"])>float(P2["Low"])): return None
    p=float(L["Close"])
    if p>float(P["High"]): return{"s":"BUY","p":p,"sl":float(P["Low"]),"sc":5}
    if p<float(P["Low"]): return{"s":"SELL","p":p,"sl":float(P["High"]),"sc":5}
    return None

def s_srsi(df,t):
    if len(df)<2: return None
    L,P=df.iloc[-1],df.iloc[-2]; p=float(L["Close"]); k=float(L["K"]); d=float(L["D"])
    pk=float(P["K"]); pd_=float(P["D"])
    if pk<=pd_ and k>d and k<25 and p>float(L["STL"]): return{"s":"BUY","p":p,"sl":float(L["STL"]),"sc":5}
    if pk>=pd_ and k<d and k>75 and p<float(L["STU"]): return{"s":"SELL","p":p,"sl":float(L["STU"]),"sc":5}
    return None

def s_mom(df,t):
    if len(df)<60: return None
    L=df.iloc[-1]; p=float(L["Close"])
    h=float(df["High"].iloc[-52:-1].max()); l=float(df["Low"].iloc[-52:-1].min()); vr=float(L["VR"])
    if p>h and vr>1.5: return{"s":"BUY","p":p,"sl":h*0.98,"sc":7}
    if p<l and vr>1.5: return{"s":"SELL","p":p,"sl":l*1.02,"sc":7}
    return None

def s_vol(df,t):
    if len(df)<25: return None
    L,P=df.iloc[-1],df.iloc[-2]; p=float(L["Close"]); vr=float(L["VR"]); a=float(L["ATR"])
    if vr<2.0 or a<=0: return None
    if p>float(P["High"]) and float(L["Close"])>float(L["Open"]): return{"s":"BUY","p":p,"sl":p-a*2,"sc":6}
    if p<float(P["Low"]) and float(L["Close"])<float(L["Open"]): return{"s":"SELL","p":p,"sl":p+a*2,"sc":6}
    return None

def s_kelt(df,t):
    L=df.iloc[-1]; p=float(L["Close"])
    if p>float(L["KCU"]) and float(L["E9"])>float(L["E21"]): return{"s":"BUY","p":p,"sl":float(L["E21"]),"sc":5}
    if p<float(L["KCL"]) and float(L["E9"])<float(L["E21"]): return{"s":"SELL","p":p,"sl":float(L["E21"]),"sc":5}
    return None

def s_don(df,t):
    L=df.iloc[-1]; p=float(L["Close"])
    if p>=float(L["DCU"])*0.999 and float(L["E9"])>float(L["E21"]): return{"s":"BUY","p":p,"sl":float(L["DCL"]),"sc":6}
    if p<=float(L["DCL"])*1.001 and float(L["E9"])<float(L["E21"]): return{"s":"SELL","p":p,"sl":float(L["DCU"]),"sc":6}
    return None

def s_psar(df,t):
    L=df.iloc[-1]; p=float(L["Close"]); a=float(L["ATR"])
    if a<=0: return None
    if p>float(L["PSAR"]) and float(L["E9"])>float(L["E21"]) and float(L["ADX"])>20: return{"s":"BUY","p":p,"sl":p-a*2,"sc":4}
    if p<float(L["STU"]) and float(L["E9"])<float(L["E21"]) and float(L["ADX"])>20: return{"s":"SELL","p":p,"sl":p+a*2,"sc":4}
    return None

def s_ha(df,t):
    if len(df)<3: return None
    L,P=df.iloc[-1],df.iloc[-2]; p=float(L["Close"]); a=float(L["ATR"])
    if a<=0: return None
    if bool(L["HB"]) and bool(P["HB"]) and float(L["E9"])>float(L["E21"]) and float(L["RSI"])>50: return{"s":"BUY","p":p,"sl":p-a*1.5,"sc":4}
    if not bool(L["HB"]) and not bool(P["HB"]) and float(L["E9"])<float(L["E21"]) and float(L["RSI"])<50: return{"s":"SELL","p":p,"sl":p+a*1.5,"sc":4}
    return None

def s_eng(df,t):
    if len(df)<2: return None
    L,P=df.iloc[-1],df.iloc[-2]; p=float(L["Close"]); a=float(L["ATR"])
    if a<=0: return None
    if float(P["Close"])<float(P["Open"]) and float(L["Close"])>float(L["Open"]) and float(L["Close"])>float(P["Open"]) and float(L["Open"])<float(P["Close"]): return{"s":"BUY","p":p,"sl":p-a*1.5,"sc":5}
    if float(P["Close"])>float(P["Open"]) and float(L["Close"])<float(L["Open"]) and float(L["Close"])<float(P["Open"]) and float(L["Open"])>float(P["Close"]): return{"s":"SELL","p":p,"sl":p+a*1.5,"sc":5}
    return None

def s_ham(df,t):
    L=df.iloc[-1]; o,h,l,c=float(L["Open"]),float(L["High"]),float(L["Low"]),float(L["Close"])
    b=abs(c-o); u=h-max(o,c); dn=min(o,c)-l
    if b<=0: return None
    a=float(L["ATR"])
    if a<=0: return None
    if dn>2*b and u<b*0.3 and float(L["RSI"])<40: return{"s":"BUY","p":c,"sl":l-a*0.5,"sc":5}
    if u>2*b and dn<b*0.3 and float(L["RSI"])>60: return{"s":"SELL","p":c,"sl":h+a*0.5,"sc":5}
    return None

def s_mr(df,t):
    L=df.iloc[-1]; p=float(L["Close"]); m=float(L["M20"]); s=float(L["S20"])
    if s<=0: return None
    z=(p-m)/s; a=float(L["ATR"])
    if a<=0: return None
    if z<-2 and float(L["RSI"])<30: return{"s":"BUY","p":p,"sl":p-a*1.5,"sc":4}
    if z>2 and float(L["RSI"])>70: return{"s":"SELL","p":p,"sl":p+a*1.5,"sc":4}
    return None

def s_mem(df,t):
    L=df.iloc[-1]; p=float(L["Close"]); a=float(L["ATR"])
    if a<=0: return None
    e9,e21,e50=float(L["E9"]),float(L["E21"]),float(L["E50"])
    if e9>e21>e50 and p>e9 and float(L["RSI"])>55 and float(L["ADX"])>20: return{"s":"BUY","p":p,"sl":e21-a*0.5,"sc":6}
    if e9<e21<e50 and p<e9 and float(L["RSI"])<45 and float(L["ADX"])>20: return{"s":"SELL","p":p,"sl":e21+a*0.5,"sc":6}
    return None

SM={"ORB":s_orb,"VWAP":s_vwap,"EMA":s_ema,"STADX":s_stadx,"BBSQ":s_bbsq,"RSID":s_rsid,"CPR":s_cpr,"MACD":s_macd,"IB":s_ib,"SRSI":s_srsi,"MOM":s_mom,"VOL":s_vol,"KELT":s_kelt,"DON":s_don,"PSAR":s_psar,"HA":s_ha,"ENG":s_eng,"HAM":s_ham,"MR":s_mr,"MEM":s_mem}

def sig(df,t,dis,st):
    B=[]; S=[]
    for n in SN:
        if n in dis: continue
        s=st.get(n,{})
        if s.get("streak_losses",0)>=ADL: continue
        if s.get("total",0)>=20 and s.get("wins",0)/max(1,s.get("total",1))<SWR: continue
        try:
            r=SM[n](df,t)
            if r and r.get("p",0)>0:
                (B if r["s"]=="BUY" else S).append({"n":n,"p":r["p"],"sl":r["sl"],"sc":r["sc"]})
        except Exception as e: print(f"[{n}] {e}")
    bs=sum(x["sc"] for x in B); ss_=sum(x["sc"] for x in S)
    if bs>=MINS and bs>ss_: return{"s":"BUY","p":B[0]["p"],"sl":max(x["sl"] for x in B),"sc":bs,"st":[x["n"] for x in B]}
    if ss_>=MINS and ss_>bs: return{"s":"SELL","p":S[0]["p"],"sl":min(x["sl"] for x in S),"sc":ss_,"st":[x["n"] for x in S]}
    return None

def qty(cap,p,sl,atr):
    rps=abs(p-sl)
    if rps<=0: return 0
    ra=cap*RISK
    if atr>0:
        ap=atr/p
        if ap>0.03: ra*=0.5
        elif ap>0.02: ra*=0.75
    q=int(ra/rps)
    mc=cap*0.25
    if q*p>mc: q=int(mc//p)
    if q*p>cap: q=int(cap//p)
    return max(0,q)

def cnt(s): return len(s.get("open_positions",[]))

def scan(s,st):
    now=datetime.now(IST); td=str(now.date())
    if s["loss_today"]>=DLL*s["starting_capital"]: return
    if s["trades_today"]>=MAXTD: return
    slots=MAXPOS-cnt(s)
    if slots<=0: return
    t=now.time(); cands=[]; seen=set()
    for sym in WL:
        if any(p["symbol"]==sym for p in s.get("open_positions",[])): continue
        if sym in seen: continue
        df=fd(sym)
        if df is None: continue
        try: df=ind(df)
        except: continue
        sg=sig(df,t,s["disabled_today"],st)
        if not sg: continue
        L=df.iloc[-1]; a=float(L["ATR"]); p=sg["p"]; sl=sg["sl"]
        if a<=0: continue
        if sg["s"]=="BUY" and sl>=p: continue
        if sg["s"]=="SELL" and sl<=p: continue
        q=qty(s["capital"],p,sl,a)
        if q<1: continue
        c=p*q
        if c>s["capital"]: continue
        rps=abs(p-sl)
        if sg["s"]=="BUY": t1=p+T1M*rps; t2=p+T2M*rps
        else: t1=p-T1M*rps; t2=p-T2M*rps
        ec=chg(p,t2,q); en=rps*T2M*q-ec
        if en<minp(): continue
        cands.append({"symbol":sym,"price":p,"sl":sl,"qty":q,"cost":c,"score":sg["sc"],"strategies":sg["st"],"side":sg["s"],"t1":t1,"t2":t2,"ec":ec,"en":en})
        seen.add(sym)
    if not cands: return
    cands.sort(key=lambda x:x["score"],reverse=True)
    taken=0
    for b in cands:
        if taken>=slots: break
        if s["trades_today"]+taken>=MAXTD: break
        if b["cost"]>s["capital"]: continue
        np_={"symbol":b["symbol"],"entry":b["price"],"qty":b["qty"],"sl":b["sl"],"initial_sl":b["sl"],"trail_high":b["price"],"target_1r":b["t1"],"target_2r":b["t2"],"side":b["side"],"strategies":b["strategies"],"entry_time":str(now),"entry_date":td,"entry_dt":now.isoformat(),"days_held":0,"partial_booked":False}
        s["open_positions"].append(np_); s["capital"]-=b["cost"]; taken+=1
        slp=abs(b["price"]-b["sl"])/b["price"]*100
        tg(f"📈 *PAPER {b['side']}*\nStock: {b['symbol']}\nPrice: ₹{b['price']:.2f}\nQty: {b['qty']}\nCost: ₹{b['cost']:.2f}\nSL: ₹{b['sl']:.2f} ({slp:.2f}%)\n1R: ₹{b['t1']:.2f}\n2R: ₹{b['t2']:.2f}\nScore: {b['score']}\nStrats: {', '.join(b['strategies'])}\nCharges: ₹{b['ec']:.2f}\nNet: ₹{b['en']:.2f}\nPos: {cnt(s)}/{MAXPOS}\nCash: ₹{s['capital']:.2f}")
    if taken>0: ss(s)

def mgr(s,st,pos):
    sym=pos["symbol"]; df=fi(sym)
    if df is None or len(df)==0: return
    try: p=float(df["Close"].iloc[-1])
    except: return
    sd=pos["side"]
    try: ed=datetime.strptime(pos.get("entry_date",str(datetime.now(IST).date())),"%Y-%m-%d").date()
    except: ed=datetime.now(IST).date()
    today=datetime.now(IST).date(); pos["days_held"]=(today-ed).days
    edt=pdt(pos.get("entry_dt")) or pdt(pos.get("entry_time"))
    if edt is None: hh=0
    else:
        if edt.tzinfo is None: edt=IST.localize(edt)
        hh=(datetime.now(IST)-edt).total_seconds()/3600
    rps=abs(pos["entry"]-pos["initial_sl"])
    if rps<=0: return
    if sd=="BUY":
        if p>pos["trail_high"]: pos["trail_high"]=p
    else:
        if p<pos["trail_high"]: pos["trail_high"]=p
    if not pos.get("partial_booked") and pos["qty"]>=2:
        h1=(sd=="BUY" and p>=pos["target_1r"]) or (sd=="SELL" and p<=pos["target_1r"])
        if h1:
            bq=int(pos["qty"]*PB)
            if bq<1: bq=1
            if bq>=pos["qty"]: bq=pos["qty"]-1
            if bq>=1:
                g=(p-pos["entry"])*bq if sd=="BUY" else (pos["entry"]-p)*bq
                ch=chg(pos["entry"],p,bq); n=g-ch; pr=pos["entry"]*bq+n
                s["capital"]+=pr; pos["qty"]-=bq; pos["partial_booked"]=True; pos["sl"]=pos["entry"]
                lt({"date":str(today),"time":str(datetime.now(IST).time()),"symbol":sym,"strategy":"PARTIAL_1R","side":sd,"entry":pos["entry"],"qty":bq,"exit":p,"gross":round(g,2),"charges":ch,"net":round(n,2),"reason":"Partial 1R","capital_after":round(s["capital"],2),"mode":MODE})
                ss(s)
                tg(f"💰 *PARTIAL 60% at 1R*\nStock: {sym}\nBooked: {bq}\nPrice: ₹{p:.2f}\nNet: ₹{n:.2f}\nSL→BE: ₹{pos['entry']:.2f}\nLeft: {pos['qty']}")
    if pos.get("partial_booked"):
        if sd=="BUY":
            ns=max(pos["sl"],p*(1-TRAIL1))
            if ns>pos["sl"]: pos["sl"]=ns; ss(s)
        else:
            ns=min(pos["sl"],p*(1+TRAIL1))
            if ns<pos["sl"]: pos["sl"]=ns; ss(s)
    else:
        if sd=="BUY":
            ns=max(pos["sl"],p*(1-TRAIL0))
            if ns>pos["sl"]: pos["sl"]=ns; ss(s)
        else:
            ns=min(pos["sl"],p*(1+TRAIL0))
            if ns<pos["sl"]: pos["sl"]=ns; ss(s)
    mr=(p-pos["entry"])/rps if sd=="BUY" else (pos["entry"]-p)/rps
    if mr>=BOOST:
        if sd=="BUY":
            ls=p*(1-0.005)
            if ls>pos["sl"]: pos["sl"]=ls; ss(s)
        else:
            ls=p*(1+0.005)
            if ls<pos["sl"]: pos["sl"]=ls; ss(s)
    ep=None; rsn=None
    if sd=="BUY":
        if p<=pos["sl"]: ep,rsn=p,"SL hit"
        elif p>=pos["target_2r"]: ep,rsn=p,"2R target"
    else:
        if p>=pos["sl"]: ep,rsn=p,"SL hit"
        elif p<=pos["target_2r"]: ep,rsn=p,"2R target"
    if not ep and hh>=NOMOVE and mr<0.5: ep,rsn=p,f"No-move ({int(hh)}h)"
    if not ep and pos["days_held"]>=HOLD:
        if (sd=="BUY" and p>pos["entry"]) or (sd=="SELL" and p<pos["entry"]): ep,rsn=p,f"Time exit ({HOLD}d, profit)"
        else: ep,rsn=p,f"Time exit ({HOLD}d)"
    if not ep: return
    g=(ep-pos["entry"])*pos["qty"] if sd=="BUY" else (pos["entry"]-ep)*pos["qty"]
    ch=chg(pos["entry"],ep,pos["qty"]); n=g-ch; pr=pos["entry"]*pos["qty"]+n
    s["capital"]+=pr; s["trades_today"]+=1
    if n<0: s["loss_today"]+=abs(n)
    for sn in pos["strategies"]:
        if sn in st:
            if n>0: st[sn]["wins"]+=1; st[sn]["streak_losses"]=0
            else: st[sn]["losses"]+=1; st[sn]["streak_losses"]+=1
            st[sn]["pnl"]=round(st[sn]["pnl"]+n,2); st[sn]["total"]=st[sn]["wins"]+st[sn]["losses"]
    sstats(st)
    lt({"date":str(today),"time":str(datetime.now(IST).time()),"symbol":sym,"strategy":"|".join(pos["strategies"]),"side":sd,"entry":pos["entry"],"qty":pos["qty"],"exit":ep,"gross":round(g,2),"charges":ch,"net":round(n,2),"reason":rsn,"capital_after":round(s["capital"],2),"mode":MODE})
    em="✅" if n>0 else "❌"
    tg(f"{em} *PAPER {sd} EXIT*\nStock: {sym}\nEntry: ₹{pos['entry']:.2f}\nExit: ₹{ep:.2f}\nQty: {pos['qty']}\nHeld: {pos['days_held']}d/{int(hh)}h\nReason: {rsn}\nGross: ₹{g:.2f}\nCharges: ₹{ch:.2f}\nNet: ₹{n:.2f}\nCash: ₹{s['capital']:.2f}")
    s["open_positions"].remove(pos); ss(s)

def sumr(per):
    if not os.path.exists(LF): return None
    try: df=pd.read_csv(LF)
    except: return None
    if len(df)==0: return None
    df["date"]=pd.to_datetime(df["date"]); today=datetime.now(IST).date()
    if per=="daily": m=df["date"].dt.date==today; ti="📊 Daily Summary"
    elif per=="weekly": m=df["date"].dt.date>=(today-timedelta(days=7)); ti="📊 Weekly Summary"
    else: m=df["date"].dt.date>=(today-timedelta(days=30)); ti="📊 Monthly Summary"
    sb=df[m]
    if len(sb)==0: return None
    t=len(sb); w=len(sb[sb["net"]>0]); l=len(sb[sb["net"]<=0]); wr=(w/t*100) if t else 0
    g=sb["gross"].sum(); c=sb["charges"].sum(); n=sb["net"].sum()
    aw=sb[sb["net"]>0]["net"].mean() if w>0 else 0; al=sb[sb["net"]<=0]["net"].mean() if l>0 else 0
    msg=f"*{ti}*\nTrades: {t} | W: {w} | L: {l}\nWin: {wr:.1f}%\nAvgW: ₹{aw:.2f} | AvgL: ₹{al:.2f}\nGross: ₹{g:.2f} | Chg: ₹{c:.2f}\n*Net: ₹{n:.2f}*\n\n*Per Strategy:*\n"
    sdf=sb[sb["strategy"]!="PARTIAL_1R"]
    for x in SN:
        sx=sdf[sdf["strategy"].str.contains(x,na=False)]
        if len(sx)==0: continue
        sw=len(sx[sx["net"]>0]); sl_=len(sx[sx["net"]<=0])
        msg+=f"• {x}: {len(sx)}T ({sw}W/{sl_}L) ₹{sx['net'].sum():.2f}\n"
    fn=f"trades_{per}_{today}.csv"; sb.to_csv(fn,index=False)
    return msg,fn

def chksum(s):
    now=datetime.now(IST); td=str(now.date()); up=False
    if now.time()>=dtime(15,35) and s.get("last_daily")!=td:
        r=sumr("daily")
        if r: tg(r[0]); tgd(r[1],"Daily log")
        s["last_daily"]=td; up=True
    if now.weekday()==5 and now.time()>=dtime(10,0):
        wk=f"{now.year}-W{now.isocalendar()[1]}"
        if s.get("last_weekly")!=wk:
            r=sumr("weekly")
            if r: tg(r[0]); tgd(r[1],"Weekly log")
            s["last_weekly"]=wk; up=True
    if now.day==1 and now.time()>=dtime(10,0):
        mk=f"{now.year}-{now.month}"
        if s.get("last_monthly")!=mk:
            r=sumr("monthly")
            if r: tg(r[0]); tgd(r[1],"Monthly log")
            s["last_monthly"]=mk; up=True
    if up: ss(s)

if __name__=="__main__":
    if not TOKEN or not CHAT_ID: print("⚠️ Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID")
    else: tg(f"🤖 *Bot v7.4 ONLINE*\nMode: DELIVERY\nCapital: ₹{CAP}\nStrategies: {len(SN)}\nStocks: {len(WL)}\nSecure: ✅")
    while True:
        try:
            now=datetime.now(IST); s=ls(); st=lstats()
            drs(s)
            if s["capital"]>s["peak_capital"]: s["peak_capital"]=s["capital"]; ss(s)
            dd=(s["peak_capital"]-s["capital"])/max(1,s["peak_capital"])
            if dd>=MDD:
                td=str(now.date())
                if s.get("drawdown_alerted")!=td:
                    tg(f"🛑 *HALTED* DD: {dd*100:.1f}%"); s["drawdown_alerted"]=td; ss(s)
            if dtime(9,15)<=now.time()<=dtime(15,30) and now.weekday()<5:
                if dd<MDD:
                    for pos in list(s.get("open_positions",[])):
                        try: mgr(s,st,pos)
                        except Exception as e: print(f"[mgr {pos.get('symbol')}] {e}")
            if dtime(9,30)<=now.time()<=dtime(15,0) and now.weekday()<5:
                if dd<MDD:
                    try: scan(s,st)
                    except Exception as e: print(f"[scan] {e}")
            chksum(s)
            time.sleep(900)
        except KeyboardInterrupt: break
        except Exception as e:
            tg(f"⚠️ Error: {str(e)[:200]}"); time.sleep(60)