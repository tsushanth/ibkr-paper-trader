"""Thin adapter between the risk-gated order flow and Interactive
Brokers' API, via ib_async (the maintained fork of ib_insync -- the
original is abandoned and breaks outright on Python 3.14's asyncio
changes, confirmed by actually hitting that error before switching).

Connected and verified for real against a live IB Gateway paper account
(see README) -- not just written to spec.

ib_async is imported lazily (inside functions, not at module load) so
the rest of this package -- and its tests -- have zero dependency on it
or on a running TWS/Gateway instance.
"""
import time

from risk_gates import RiskGate, KillSwitchTripped


class GatedOrderRouter:
    """Wraps IBKR order submission so every order passes through the
    RiskGate first. Strategy code should never call ib_async directly --
    it should only ever go through this class.
    """

    def __init__(self, risk_gate: RiskGate, host: str = "127.0.0.1", port: int = 4002, client_id: int = 1):
        # Port depends on which app you're running, and they DIFFER --
        # confirmed the hard way (7497 wasn't reachable; 4002 was):
        #   TWS paper = 7497, TWS live = 7496
        #   IB Gateway paper = 4002, IB Gateway live = 4001
        # Defaulting to Gateway's paper port since that's what this
        # project actually runs against. Switching to a live port
        # should be an explicit, reviewed change, not a default.
        self.risk_gate = risk_gate
        self.host = host
        self.port = port
        self.client_id = client_id
        self.ib = None

    def connect(self):
        from ib_async import IB
        self.ib = IB()
        self.ib.connect(self.host, self.port, clientId=self.client_id)
        return self.ib

    def submit_limit_order(self, symbol: str, side: str, qty: float, limit_price: float):
        if self.ib is None:
            raise RuntimeError("not connected -- call connect() first")

        from ib_async import Stock, LimitOrder

        now = time.time()
        self.risk_gate.check_order(symbol, side, qty, limit_price, now)  # raises on breach

        contract = Stock(symbol, "SMART", "USD")
        order = LimitOrder(side, qty, limit_price)
        trade = self.ib.placeOrder(contract, order)
        self.risk_gate.record_order_sent(now)
        return trade

    def on_fill(self, symbol: str, side: str, qty: float, fill_price: float, entry_price: float | None = None):
        """Call this from an ib_async fill-event callback to keep the
        risk gate's position/pnl state in sync with reality.
        """
        self.risk_gate.record_fill(symbol, side, qty, fill_price, entry_price)
