from datetime import date
from decimal import Decimal

from bot.risk import (
    kelly_fraction,
    resolve_day_start_bankroll,
    should_halt_for_loss,
)


def test_kelly_zero_on_bad_price():
    assert kelly_fraction(0.6, 0) == 0.0
    assert kelly_fraction(0.6, 1) == 0.0


def test_kelly_positive_edge():
    k = kelly_fraction(0.7, 0.4)
    assert k > 0
    assert abs(k - (0.3 / 0.6)) < 1e-9


def test_kelly_no_edge():
    assert kelly_fraction(0.4, 0.5) == 0.0


def test_should_halt_for_loss():
    start = Decimal("100")
    assert should_halt_for_loss(start, Decimal("90"), 0.10) is True
    assert should_halt_for_loss(start, Decimal("91"), 0.10) is False
    assert should_halt_for_loss(Decimal("0"), Decimal("0"), 0.10) is False


def test_resolve_day_start_resets_on_new_day():
    day, start, wrote = resolve_day_start_bankroll(
        stored_day="2026-10-01",
        stored_start="100",
        bankroll=Decimal("80"),
        today=date(2026, 10, 2),
    )
    assert day == "2026-10-02"
    assert start == Decimal("80")
    assert wrote is True


def test_resolve_day_start_keeps_same_day_baseline():
    day, start, wrote = resolve_day_start_bankroll(
        stored_day="2026-10-02",
        stored_start="100",
        bankroll=Decimal("80"),
        today=date(2026, 10, 2),
    )
    assert day == "2026-10-02"
    assert start == Decimal("100")
    assert wrote is False
