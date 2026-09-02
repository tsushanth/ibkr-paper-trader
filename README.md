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

## Status: connected and verified end-to-end against a real IB Gateway paper account

Uses **ib_async** (the maintained fork of ib_insync — the original is
abandoned and fails outright on Python 3.14's asyncio changes; hit that
error directly, switched rather than working around it).

- **Real and tested:** `src/risk_gates.py` (6/6 unit tests) plus a real
  connection test — order placed against the live paper account,
  confirmed, cancelled, and an oversized order correctly blocked by the
  risk gate before ever reaching IBKR.
- **Port note, learned the hard way:** IB **Gateway**'s paper port is
  **4002**, not TWS's 7497 — the two apps use different ports entirely.
  This repo defaults to 4002 since Gateway (not full TWS) is what's
  actually running for this project.
- **Not yet exercised:** `src/ibkr_options_data.py` (historical IV
  fetcher) — the connection works, but pulling a real IV series to feed
  `mm-backtester` hasn't happened yet.

## First-run checklist

1. Install IB Gateway (lighter-weight than full TWS, recommended), log
   into a **paper** account, enable API access (Configure → Settings →
   API → Settings → check "Enable ActiveX and Socket Clients", confirm
   port **4002** for Gateway paper — 7497 is TWS's port, not Gateway's).
2. `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
3. Confirm `ibkr_options_data.fetch_option_chain_strikes()` returns real
   expirations/strikes for a liquid symbol (e.g. SPY).
4. Pull a small `fetch_historical_iv()` series for one strike/expiry,
   confirm it's non-empty and plausible (roughly 0.1–1.0).
5. ✅ Done — a real order through `ibkr_adapter.py`'s `GatedOrderRouter`
   has been placed, confirmed, and cancelled against the paper account.

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
