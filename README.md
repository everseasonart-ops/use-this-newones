# Wiggles Structure Scalper v0.1

Shadow-only MFP perpetual-market scanner derived from the proven connection/stream pattern in the previous Wiggles bot.

## v0.1 behaviour
- Discovers available MFP perp markets automatically.
- Reads 1-minute and 15-minute candles.
- Uses 15m EMA context plus 1m EMA 9/21, VWAP, displacement and micro structure.
- Looks for BOS -> pullback/reclaim rather than chasing the breakout.
- Calculates a proposed $35-risk position with a $40 hard risk ceiling concept.
- Requires at least 1.5R / $60 reward reference.
- Records the intended management rule: confirmed 1m HL/LH trailing, never loosen the stop.
- **Cannot place orders. There is no order-placement code in v0.1.**

## Render environment variable
Only one secret is required initially:

`FP_API_KEY` = your existing MFP API key

Optional advanced overrides are in `config.py`; leave them alone for the first test.

## Health/status
Open the Render service URL or `/status` after deployment. You want to see:
- `api_authenticated: true`
- `market_count` greater than 0
- workers connected
- `mode: SHADOW`
- `order_execution: HARD BLOCKED IN v0.1`

`/signals` shows recent simulated setups.
