# Wiggles Structure Scalper
# Version 0.1
# SHADOW MODE - NO LIVE ORDERS

import os
import time
from datetime import datetime, timezone

VERSION = "0.1"
MODE = os.getenv("MODE", "SHADOW")
EXECUTION_ENABLED = False

# Risk settings
RISK_PER_TRADE_USD = 35.0
MAX_RISK_PER_TRADE_USD = 40.0
MIN_REWARD_USD = 60.0
MIN_RR = 1.5

MAX_TRADES_PER_DAY = 3
DAILY_LOSS_LIMIT_USD = 100.0
MAX_OPEN_POSITIONS = 1


def startup():
    print("=" * 50)
    print("WIGGLES STRUCTURE SCALPER")
    print(f"Version: {VERSION}")
    print(f"Mode: {MODE}")
    print(f"Execution enabled: {EXECUTION_ENABLED}")
    print("=" * 50)

    print(f"Risk per trade: ${RISK_PER_TRADE_USD:.2f}")
    print(f"Maximum risk: ${MAX_RISK_PER_TRADE_USD:.2f}")
    print(f"Minimum reward: ${MIN_REWARD_USD:.2f}")
    print(f"Minimum R:R: {MIN_RR}")
    print(f"Daily loss limit: ${DAILY_LOSS_LIMIT_USD:.2f}")
    print(f"Maximum trades/day: {MAX_TRADES_PER_DAY}")

    if EXECUTION_ENABLED:
        raise RuntimeError(
            "SAFETY LOCK: v0.1 must remain in SHADOW mode."
        )

    print("Safety lock: ACTIVE")
    print("LIVE ORDERS CANNOT BE PLACED")


def run():
    startup()

    while True:
        now = datetime.now(timezone.utc)

        print(
            f"[{now.isoformat()}] "
            "Structure Scalper running - SHADOW"
        )

        time.sleep(30)


if __name__ == "__main__":
    run()
