from collections import deque
from dataclasses import dataclass
from math import isfinite
from config import *

@dataclass
class Candle:
    t: int
    o: float
    h: float
    l: float
    c: float
    v: float = 0.0

def ema(values, length):
    if len(values) < length: return None
    k = 2.0 / (length + 1.0)
    out = sum(values[:length]) / length
    for x in values[length:]: out = x * k + out * (1-k)
    return out

def atr(bars, length=14):
    if len(bars) < length + 1: return None
    trs=[]
    for i in range(1,len(bars)):
        b,p=bars[i],bars[i-1]
        trs.append(max(b.h-b.l, abs(b.h-p.c), abs(b.l-p.c)))
    return sum(trs[-length:]) / length

def vwap(bars, n=60):
    xs=list(bars)[-n:]
    den=sum(max(b.v,0.0) for b in xs)
    if den <= 0: return None
    return sum(((b.h+b.l+b.c)/3.0)*max(b.v,0.0) for b in xs)/den

class StructureScalperEngine:
    def __init__(self, provider, symbol):
        self.provider=provider; self.symbol=symbol
        self.bars1=deque(maxlen=300); self.bars15=deque(maxlen=160)
        self.pending=None; self.bar_index=-1; self.last_signal_bar=-999
        self.last_pivot_high=None; self.last_pivot_low=None

    def add_15m(self,b):
        if self.bars15 and self.bars15[-1].t==b.t: self.bars15[-1]=b
        else: self.bars15.append(b)

    def _context(self):
        if len(self.bars15)<EMA_SLOW+2: return {"bias":"warming"}
        closes=[b.c for b in self.bars15]
        f=ema(closes,EMA_FAST); s=ema(closes,EMA_SLOW); px=closes[-1]
        if f>s and px>s: bias="long"
        elif f<s and px<s: bias="short"
        else: bias="mixed"
        return {"bias":bias,"ema9":f,"ema21":s}

    def _pivot(self):
        n=PIVOT_LEN
        xs=list(self.bars1)
        if len(xs)<2*n+1: return
        i=len(xs)-1-n; b=xs[i]
        left=xs[i-n:i]; right=xs[i+1:i+n+1]
        if all(b.h>x.h for x in left+right): self.last_pivot_high=(b.h,i)
        if all(b.l<x.l for x in left+right): self.last_pivot_low=(b.l,i)

    def _make_signal(self,side,b,a,level,stop,ctx,reason):
        risk_dist=(b.c-stop) if side=="LONG" else (stop-b.c)
        if risk_dist<=0 or not isfinite(risk_dist): return None
        # For linear USD-margined perps, size * price distance approximates USD P/L.
        # This is SHADOW sizing only; provider quote validation will be required before live mode.
        size=RISK_PER_TRADE_USD/risk_dist
        target=(b.c + max(risk_dist*MIN_RR, MIN_REWARD_USD/max(size,1e-12))) if side=="LONG" else (b.c - max(risk_dist*MIN_RR, MIN_REWARD_USD/max(size,1e-12)))
        return {"provider":self.provider,"symbol":self.symbol,"side":side,"entry":b.c,"initial_stop":stop,
                "structure_level":level,"risk_distance":risk_dist,"shadow_size":size,"planned_risk_usd":RISK_PER_TRADE_USD,
                "hard_max_risk_usd":MAX_RISK_PER_TRADE_USD,"minimum_reward_usd":MIN_REWARD_USD,"minimum_rr":MIN_RR,
                "runner_trigger_usd":MIN_REWARD_USD,"initial_target_reference":target,"context":ctx,"reason":reason,
                "management":"trail only after confirmed 1m HL/LH; never loosen stop","bar_time":b.t,"shadow":True}

    def add_1m(self,b):
        if self.bars1 and self.bars1[-1].t==b.t: self.bars1[-1]=b; return []
        self.bars1.append(b); self.bar_index+=1; self._pivot()
        if len(self.bars1)<max(EMA_SLOW+3,ATR_LEN+3): return []
        xs=list(self.bars1); closes=[x.c for x in xs]; a=atr(xs,ATR_LEN)
        if not a or a<=0: return []
        f=ema(closes,EMA_FAST); s=ema(closes,EMA_SLOW); vw=vwap(xs)
        ctx=self._context(); body=abs(b.c-b.o)
        bull_momentum=f>s and (vw is None or b.c>=vw)
        bear_momentum=f<s and (vw is None or b.c<=vw)

        # Arm after a close through confirmed micro structure with displacement.
        if self.last_pivot_high and b.c>self.last_pivot_high[0] and body>=a*DISPLACEMENT_ATR and bull_momentum and ctx["bias"] in ("long","mixed"):
            self.pending={"side":"LONG","level":self.last_pivot_high[0],"armed":self.bar_index,"extreme":b.l}
        elif self.last_pivot_low and b.c<self.last_pivot_low[0] and body>=a*DISPLACEMENT_ATR and bear_momentum and ctx["bias"] in ("short","mixed"):
            self.pending={"side":"SHORT","level":self.last_pivot_low[0],"armed":self.bar_index,"extreme":b.h}

        p=self.pending
        if not p: return []
        age=self.bar_index-p["armed"]
        if age<=0: return []
        if age>MAX_RETEST_BARS: self.pending=None; return []
        tol=a*RETEST_TOLERANCE_ATR; sig=None
        if p["side"]=="LONG":
            p["extreme"]=min(p["extreme"],b.l)
            touched=b.l<=p["level"]+tol
            held=touched and b.c>p["level"] and b.c>b.o and bull_momentum
            failed=b.c<p["level"]-tol
            if failed: self.pending=None
            elif held and self.bar_index-self.last_signal_bar>=COOLDOWN_BARS:
                stop=p["extreme"]-tol*0.25
                sig=self._make_signal("LONG",b,a,p["level"],stop,ctx,"1m BOS -> pullback/reclaim + EMA/VWAP + 15m context")
        else:
            p["extreme"]=max(p["extreme"],b.h)
            touched=b.h>=p["level"]-tol
            held=touched and b.c<p["level"] and b.c<b.o and bear_momentum
            failed=b.c>p["level"]+tol
            if failed: self.pending=None
            elif held and self.bar_index-self.last_signal_bar>=COOLDOWN_BARS:
                stop=p["extreme"]+tol*0.25
                sig=self._make_signal("SHORT",b,a,p["level"],stop,ctx,"1m BOS -> pullback/reclaim + EMA/VWAP + 15m context")
        if sig:
            self.last_signal_bar=self.bar_index; self.pending=None; return [sig]
        return []
