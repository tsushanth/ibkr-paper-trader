"""Thin adapter between the risk-gated order flow and Interactive
Brokers' API, via ib_insync.

NOT RUN OR CONNECTED as part of this project -- there is no IBKR
account/credentials available in the environment this was built in.
This is written to the documented ib_insync interface and is a
reasonable starting point, but treat it as unverified until it's
actually been run against a paper account. See README's "first real run
checklist" before trusting this code with even paper capital, let alone
live.

ib_insync is imported lazily (inside functions, not at module load) so
the rest of this package -- and its tests -- have zero dependency on it
or on a running TWS/Gateway instance.
"""
import time

from risk_gates import RiskGate, KillSwitchTripped


class GatedOrderRouter:
    """Wraps IBKR order submission so every order passes through the
    RiskGate first. Strategy code should never call ib_insync directly --
    it should only ever go through this class.
    """

    def __init__(self, risk_gate: RiskGate, host: str = "127.0.0.1", port: int = 7497, client_id: int = 1):
        # port 7497 = TWS paper trading (7496 = TWS live, 4002/4001 = Gateway paper/live).
        # Defaulting to the paper port is deliberate -- switching to a
        # live port should be an explicit, reviewed change, not a default.
        self.risk_gate = risk_gate
        self.host = host
        self.port = port
        self.client_id = client_id
        self.ib = None

    def connect(self):
        from ib_insync import IB
        self.ib = IB()
        self.ib.connect(self.host, self.port, clientId=self.client_id)
        return self.ib

    def submit_limit_order(self, symbol: str, side: str, qty: float, limit_price: float):
        if self.ib is None:
            raise RuntimeError("not connected -- call connect() first")

        from ib_insync import Stock, LimitOrder

        now = time.time()
        self.risk_gate.check_order(symbol, side, qty, limit_price, now)  # raises on breach

        contract = Stock(symbol, "SMART", "USD")
        order = LimitOrder(side, qty, limit_price)
        trade = self.ib.placeOrder(contract, order)
        self.risk_gate.record_order_sent(now)
        return trade

    def on_fill(self, symbol: str, side: str, qty: float, fill_price: float, entry_price: float | None = None):
        """Call this from an ib_insync fill-event callback to keep the
        risk gate's position/pnl state in sync with reality.
        """
        self.risk_gate.record_fill(symbol, side, qty, fill_price, entry_price)
