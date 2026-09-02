# ibkr-paper-trader

A second broker integration alongside
[alpaca-paper-trader](https://github.com/tsushanth/alpaca-paper-trader)
— not for redundancy on the same strategy, but because IBKR provides
something Alpaca doesn't: **real historical implied-volatility data**
(`reqHistoricalData` with `whatToShow="OPTION_IMPLIED_VOLATILITY"`),
free with an account. That's the one thing [mm-backtester](https://github.com/tsushanth/mm-backtester)'s
options vol-mispricing strategy has been missing since Phase 3 — its
backtest currently runs on synthetic data with explicitly flagged,
untrustworthy results (100% win rate, Sharpe 28) precisely because no
free real options-data source was available. This repo exists to close
that gap, not to duplicate the pairs strategy Alpaca already runs.

## Status: written, not yet run — needs your TWS/Gateway connection

Same situation Phase 4 was originally in with IBKR: nothing here has
connected to a live or paper IBKR account yet, because no TWS/Gateway
instance was running when this was built.

- **Real and tested:** `src/risk_gates.py` — copied from
  alpaca-paper-trader, framework-independent, 6/6 unit tests passing.
- **Written but not run:** `src/ibkr_adapter.py` (order execution) and
  `src/ibkr_options_data.py` (historical IV fetcher) — both written to
  ib_insync's documented interface, neither actually exercised yet.

## First-run checklist

1. Install TWS or IB Gateway, log into a **paper** account, enable API
   access (Edit → Global Configuration → API → Settings, port 7497 for
   paper TWS).
2. `pip install -r requirements.txt`
3. Confirm `ibkr_options_data.fetch_option_chain_strikes()` returns real
   expirations/strikes for a liquid symbol (e.g. SPY) — this is the
   first real signal the connection works.
4. Pull a small `fetch_historical_iv()` series for one strike/expiry,
   confirm it's non-empty and the values look like plausible IV
   (roughly 0.1–1.0, not garbage).
5. Only then attempt a real order through `ibkr_adapter.py`'s
   `GatedOrderRouter`, same pattern as alpaca-paper-trader's
   `live_connection_check.py`.

## Once real IV data is confirmed working

Swap it into `mm-backtester/src/synthetic_data.py`'s role — same
walk-forward harness (`run_backtest.py`), just fed real strikes/expiries
pulled via this repo instead of a generator with injected outcomes.
Expect the Sharpe to come down from the synthetic run's inflated
number; that's the real result, not a regression.

## Structure

- `src/risk_gates.py` — hard safety limits (position/notional/daily-loss/
  order-rate), identical to alpaca-paper-trader's version.
- `src/ibkr_adapter.py` — order execution, routes through the risk gate.
- `src/ibkr_options_data.py` — historical IV fetcher, the actual reason
  this repo exists.
- `tests/test_risk_gates.py` — 6 tests, all passing, no broker needed.
