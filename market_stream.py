import json, threading, time, itertools
from collections import defaultdict
import websocket
from config import WS_URL, CANDLE_INTERVALS, HISTORY_LIMIT, MAX_SYMBOLS_PER_SUB
from strategy import StructureScalperEngine, Candle

def _items(payload):
    if isinstance(payload,list): return payload
    if isinstance(payload,dict):
        for key in ("data","markets","items","results"):
            if isinstance(payload.get(key),list): return payload[key]
    return []

def normalize_markets(payload):
    out=[]; seen=set()
    for m in _items(payload):
        if not isinstance(m,dict): continue
        coin,provider=m.get("coin"),m.get("provider"); mid=m.get("id") or m.get("market_id")
        if not coin and isinstance(mid,str) and "|" in mid:
            p,c=mid.split("|",1); provider=provider or p; coin=coin or c
        if coin and provider and provider!="fpx" and (provider,coin) not in seen:
            seen.add((provider,coin)); out.append({"provider":str(provider),"coin":str(coin),"id":mid or f"{provider}|{coin}"})
    return out

def _num(x):
    try:return float(x)
    except:return None

def event_to_candle(e):
    t=e.get("openTime",e.get("startTime",e.get("timestamp")))
    vals=[_num(e.get(k)) for k in ("open","high","low","close")]; v=_num(e.get("volume",0)) or 0.0
    if t is None or any(x is None for x in vals): return None
    return Candle(int(t),*vals,v)

class MultiMarketScanner:
    def __init__(self):
        self.engines={}; self.signals=[]; self.lock=threading.Lock(); self.worker_state={}; self.final_candles=0; self.last_event_ms=None
    def status_cb(self,wid,state,err=None):
        with self.lock:self.worker_state[str(wid)]={"state":state,"error":err}
    def on_event(self,e):
        if e.get("type")!="candle" or not e.get("isFinal"):return
        provider,symbol,interval=e.get("provider"),e.get("symbol"),e.get("interval")
        if not provider or not symbol or interval not in CANDLE_INTERVALS:return
        b=event_to_candle(e)
        if not b:return
        key=(provider,symbol)
        with self.lock:
            eng=self.engines.get(key)
            if eng is None:eng=StructureScalperEngine(provider,symbol);self.engines[key]=eng
        sigs=[]
        if interval=="15m":eng.add_15m(b)
        elif interval=="1m":sigs=eng.add_1m(b)
        with self.lock:
            self.final_candles+=1;self.last_event_ms=int(time.time()*1000)
            for s in sigs:
                self.signals.append(s);self.signals=self.signals[-100:]
                print("[SHADOW SCALP] "+json.dumps(s,separators=(",",":")),flush=True)
    def summary(self):
        with self.lock:
            engines=list(self.engines.values());ready=sum(1 for e in engines if len(e.bars1)>=30 and len(e.bars15)>=24)
            return {"engines":len(engines),"engines_ready":ready,"engines_warming_up":len(engines)-ready,
                    "readiness_requirement":{"1m_bars":30,"15m_bars":24},"final_candles_received":self.final_candles,
                    "last_event_ms":self.last_event_ms,"stream_workers":len(self.worker_state),"workers":dict(self.worker_state),
                    "shadow_signal_count":len(self.signals),"recent_shadow_signals":list(self.signals[-10:])}

class Worker(threading.Thread):
    daemon=True
    def __init__(self,wid,provider,symbols,scanner):super().__init__();self.wid=wid;self.provider=provider;self.symbols=symbols;self.scanner=scanner
    def run(self):
        wait=2
        while True:
            try:
                ws=websocket.create_connection(WS_URL,timeout=45);self.scanner.status_cb(self.wid,"connected")
                ws.send(json.dumps({"op":"sub","id":1,"channel":"candles","payload":{"symbols":self.symbols,"providers":[self.provider],"intervals":CANDLE_INTERVALS,"historyLimit":0}}))
                req_id=itertools.count(2)
                for symbol in self.symbols:
                    for interval in CANDLE_INTERVALS:
                        rid=next(req_id);ws.send(json.dumps({"op":"req","id":rid,"method":"candles.history","payload":{"provider":self.provider,"symbol":symbol,"interval":interval,"limit":HISTORY_LIMIT}}))
                        while True:
                            frame=json.loads(ws.recv())
                            if frame.get("op")=="events":
                                for e in frame.get("events",[]):self.scanner.on_event(e)
                            elif frame.get("op")=="res" and frame.get("id")==rid:
                                for e in frame.get("result") or []:
                                    if isinstance(e,dict):
                                        e.setdefault("type","candle");e.setdefault("provider",self.provider);e.setdefault("symbol",symbol);e.setdefault("interval",interval);e.setdefault("isFinal",True);self.scanner.on_event(e)
                                break
                            elif frame.get("op")=="err" and frame.get("id")==rid:
                                print(f"[HISTORY WARN] {self.provider} {symbol} {interval}: {frame.get('error')}",flush=True);break
                while True:
                    frame=json.loads(ws.recv())
                    if frame.get("op")=="events":
                        for e in frame.get("events",[]):self.scanner.on_event(e)
                    elif frame.get("op") in ("sub_err","err","draining","end"):raise RuntimeError(str(frame.get("error") or frame.get("op")))
            except Exception as ex:
                self.scanner.status_cb(self.wid,"retrying",f"{type(ex).__name__}: {ex}");time.sleep(wait);wait=min(wait*2,60)

def start_workers(markets,scanner):
    grouped=defaultdict(list)
    for m in markets:grouped[m["provider"]].append(m["coin"])
    workers=[];wid=0
    for provider,symbols in grouped.items():
        syms=sorted(set(symbols))
        for i in range(0,len(syms),MAX_SYMBOLS_PER_SUB):
            wid+=1;w=Worker(wid,provider,syms[i:i+MAX_SYMBOLS_PER_SUB],scanner);workers.append(w);w.start()
    return workers
