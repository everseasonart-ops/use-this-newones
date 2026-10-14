import json, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from config import *
from fp_client import FPClient
from market_stream import MultiMarketScanner, normalize_markets, start_workers, _items

LOCK=threading.Lock();SCANNER=None;WORKERS=[]
STATE={"service":"Wiggles Structure Scalper","version":VERSION,"profile":PROFILE_NAME,"mode":"SHADOW",
       "order_execution":"HARD BLOCKED IN v0.1","api_authenticated":False,"account_count":None,"market_count":0,"providers":[],"error":None}

def bootstrap():
    global SCANNER,WORKERS
    try:
        c=FPClient();accounts=c.list_accounts();markets=normalize_markets(c.list_markets());providers=sorted(set(x["provider"] for x in markets))
        SCANNER=MultiMarketScanner()
        with LOCK:STATE.update(api_authenticated=True,account_count=len(_items(accounts)),market_count=len(markets),providers=providers,error=None)
        WORKERS=start_workers(markets,SCANNER)
        print(f"[{VERSION}] markets={len(markets)} workers={len(WORKERS)} MODE=SHADOW EXECUTION=HARD_BLOCKED",flush=True)
    except Exception as e:
        with LOCK:STATE["error"]=f"{type(e).__name__}: {e}"
        print("[BOOTSTRAP FAILED]",type(e).__name__,str(e),flush=True)

def status():
    with LOCK:s=dict(STATE)
    s["scanner"]=SCANNER.summary() if SCANNER else {"starting":True}
    s["strategy"]={"execution_tf":"1m","context_tf":"15m","ema":"9/21","vwap":True,"trigger":"micro BOS + pullback/reclaim",
        "risk_per_trade_usd":RISK_PER_TRADE_USD,"hard_max_risk_usd":MAX_RISK_PER_TRADE_USD,"minimum_reward_usd":MIN_REWARD_USD,
        "minimum_rr":MIN_RR,"proposed_max_trades_per_day":MAX_TRADES_PER_DAY,"proposed_daily_loss_limit_usd":DAILY_LOSS_LIMIT_USD,
        "runner":"after +$60, trail confirmed 1m structure; never loosen","orders_enabled":False}
    return s

class Handler(BaseHTTPRequestHandler):
    def sendj(self,code,x):
        b=json.dumps(x,indent=2,default=str).encode();self.send_response(code);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
    def do_GET(self):
        if self.path in ("/","/status"):self.sendj(200,status())
        elif self.path=="/signals":self.sendj(200,{"signals":SCANNER.summary()["recent_shadow_signals"] if SCANNER else []})
        elif self.path=="/health":
            s=status();ok=s["api_authenticated"] and s["market_count"]>0;self.sendj(200 if ok else 503,{"ok":ok,"version":VERSION,"mode":"SHADOW"})
        else:self.sendj(404,{"error":"not found"})
    def log_message(self,*args):pass

if __name__=="__main__":
    print(f"WIGGLES STRUCTURE SCALPER — {VERSION}",flush=True);print("ORDER EXECUTION: HARD BLOCKED",flush=True)
    threading.Thread(target=bootstrap,daemon=True).start();ThreadingHTTPServer(("0.0.0.0",PORT),Handler).serve_forever()
