import os

VERSION = "0.1.0-shadow"
PROFILE_NAME = "WIGGLES_STRUCTURE_SCALPER"

API_BASE = os.getenv("FP_API_BASE", "https://developers.myfundedperpetuals.com")
WS_URL = os.getenv("FP_WS_URL", "wss://api-stream.myfundedperpetuals.com/v1/market-data")
FP_API_KEY = os.getenv("FP_API_KEY", "")
PORT = int(os.getenv("PORT", "10000"))

# v0.1 is deliberately hard locked to shadow mode.
EXECUTION_ENABLED = False

# Scanner
CANDLE_INTERVALS = ["1m", "15m"]
HISTORY_LIMIT = int(os.getenv("HISTORY_LIMIT", "120"))
MAX_SYMBOLS_PER_SUB = int(os.getenv("MAX_SYMBOLS_PER_SUB", "32"))

# Strategy
EMA_FAST = 9
EMA_SLOW = 21
PIVOT_LEN = 2
ATR_LEN = 14
DISPLACEMENT_ATR = float(os.getenv("DISPLACEMENT_ATR", "0.35"))
RETEST_TOLERANCE_ATR = float(os.getenv("RETEST_TOLERANCE_ATR", "0.18"))
MAX_RETEST_BARS = int(os.getenv("MAX_RETEST_BARS", "8"))
COOLDOWN_BARS = int(os.getenv("COOLDOWN_BARS", "5"))

# Proposed live-risk settings (shadow calculations only in v0.1)
RISK_PER_TRADE_USD = float(os.getenv("RISK_PER_TRADE_USD", "35"))
MAX_RISK_PER_TRADE_USD = float(os.getenv("MAX_RISK_PER_TRADE_USD", "40"))
MIN_REWARD_USD = float(os.getenv("MIN_REWARD_USD", "60"))
MIN_RR = float(os.getenv("MIN_RR", "1.5"))
MAX_TRADES_PER_DAY = int(os.getenv("MAX_TRADES_PER_DAY", "3"))
DAILY_LOSS_LIMIT_USD = float(os.getenv("DAILY_LOSS_LIMIT_USD", "100"))
