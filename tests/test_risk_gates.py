import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from risk_gates import RiskGate, RiskLimits, KillSwitchTripped


def make_gate(**overrides):
    defaults = dict(max_position_per_symbol=100, max_total_notional=100_000,
                     max_daily_loss=500, max_orders_per_minute=5)
    defaults.update(overrides)
    return RiskGate(limits=RiskLimits(**defaults))


def test_order_within_limits_is_allowed():
    gate = make_gate()
    gate.check_order("AAPL", "BUY", 10, price=150.0, now=0.0)  # should not raise


def test_position_limit_blocks_oversized_order():
    gate = make_gate(max_position_per_symbol=50)
    try:
        gate.check_order("AAPL", "BUY", 60, price=150.0, now=0.0)
        assert False, "expected ValueError"
    except ValueError as e:
        assert "position" in str(e)


def test_daily_loss_trips_kill_switch_and_blocks_future_orders():
    gate = make_gate(max_daily_loss=100)
    gate.realized_pnl = -150
    try:
        gate.check_order("AAPL", "BUY", 1, price=150.0, now=0.0)
        assert False, "expected KillSwitchTripped"
    except KillSwitchTripped:
        pass

    assert gate.is_tripped()
    try:
        gate.check_order("MSFT", "BUY", 1, price=300.0, now=1.0)
        assert False, "kill switch should block unrelated symbols too"
    except KillSwitchTripped:
        pass


def test_kill_switch_does_not_auto_reset():
    gate = make_gate(max_daily_loss=100)
    gate.realized_pnl = -150
    try:
        gate.check_order("AAPL", "BUY", 1, price=150.0, now=0.0)
    except KillSwitchTripped:
        pass

    gate.realized_pnl = 0  # pnl recovers, but switch stays tripped until manual_reset()
    try:
        gate.check_order("AAPL", "BUY", 1, price=150.0, now=2.0)
        assert False, "should still be tripped"
    except KillSwitchTripped:
        pass

    gate.manual_reset()
    gate.check_order("AAPL", "BUY", 1, price=150.0, now=3.0)  # now allowed


def test_order_rate_limit_blocks_runaway_loop():
    gate = make_gate(max_orders_per_minute=3)
    for i in range(3):
        gate.check_order("AAPL", "BUY", 1, price=150.0, now=float(i))
        gate.record_order_sent(float(i))

    try:
        gate.check_order("AAPL", "BUY", 1, price=150.0, now=3.5)
        assert False, "4th order within 60s should be blocked"
    except ValueError as e:
        assert "orders in the last 60s" in str(e)


def test_record_fill_updates_position_and_pnl():
    gate = make_gate()
    gate.record_fill("AAPL", "BUY", 10, price=150.0)
    assert gate.positions["AAPL"] == 10

    gate.record_fill("AAPL", "SELL", 10, price=155.0, entry_price=150.0)
    assert gate.positions["AAPL"] == 0
    assert abs(gate.realized_pnl - 50.0) < 1e-9


if __name__ == "__main__":
    test_order_within_limits_is_allowed()
    test_position_limit_blocks_oversized_order()
    test_daily_loss_trips_kill_switch_and_blocks_future_orders()
    test_kill_switch_does_not_auto_reset()
    test_order_rate_limit_blocks_runaway_loop()
    test_record_fill_updates_position_and_pnl()
    print("all tests passed")
