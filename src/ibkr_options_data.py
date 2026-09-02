"""The actual reason this repo exists alongside alpaca-paper-trader:
IBKR's historical data API uniquely supports `whatToShow="OPTION_IMPLIED_VOLATILITY"`
-- a real historical IV time series per contract, which is not available
for free through Alpaca or yfinance. This is what could replace
mm-backtester's synthetic_data.py generator with genuine historical
options data, the gap flagged in that project's README since Phase 3.

Uses ib_async (the maintained fork of ib_insync -- the original is
abandoned and breaks outright on Python 3.14's asyncio changes,
confirmed by hitting that error directly before switching).
"""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class IVBar:
    date: datetime
    implied_vol: float
    underlying_price: float


def fetch_historical_iv(host: str, port: int, client_id: int,
                         symbol: str, expiry: str, strike: float, right: str,
                         duration: str = "6 M", bar_size: str = "1 day") -> list[IVBar]:
    """Fetches a real historical implied-vol series for one option
    contract. `expiry` as 'YYYYMMDD', `right` as 'C' or 'P'.

    This is IBKR-specific -- reqHistoricalData with whatToShow=
    'OPTION_IMPLIED_VOLATILITY' is not something Alpaca's or yfinance's
    APIs expose. Getting a full vol *surface* history means calling this
    once per (strike, expiry) pair you care about -- expect IBKR's
    pacing/rate limits to matter if pulling many contracts at once.
    """
    from ib_async import IB, Option

    ib = IB()
    ib.connect(host, port, clientId=client_id)
    try:
        contract = Option(symbol, expiry, strike, right, "SMART")
        ib.qualifyContracts(contract)

        bars = ib.reqHistoricalData(
            contract, endDateTime="", durationStr=duration,
            barSizeSetting=bar_size, whatToShow="OPTION_IMPLIED_VOLATILITY",
            useRTH=True,
        )
        # Underlying price isn't part of this IV bar -- pull it separately
        # (e.g. a plain Stock contract with whatToShow="TRADES") and join
        # by date if the caller needs both series together.
        return [IVBar(date=b.date, implied_vol=b.close, underlying_price=float("nan")) for b in bars]
    finally:
        ib.disconnect()


def fetch_option_chain_strikes(host: str, port: int, client_id: int, symbol: str) -> dict:
    """Fetches the available expiries/strikes for a symbol -- the first
    call you'd make before deciding which (strike, expiry) pairs to
    pull historical IV for via fetch_historical_iv above.
    """
    from ib_async import IB, Stock

    ib = IB()
    ib.connect(host, port, clientId=client_id)
    try:
        stock = Stock(symbol, "SMART", "USD")
        ib.qualifyContracts(stock)
        chains = ib.reqSecDefOptParams(stock.symbol, "", stock.secType, stock.conId)
        return {
            "expirations": sorted(chains[0].expirations) if chains else [],
            "strikes": sorted(chains[0].strikes) if chains else [],
        }
    finally:
        ib.disconnect()
