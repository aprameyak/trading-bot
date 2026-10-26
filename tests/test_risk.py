from datetime import date
from decimal import Decimal

from bot.executor import open_positions, positions_value
from bot.kalshi_client import Market
from bot.risk import (
    fee_adjusted_edge,
    kalshi_fee,
    kelly_fraction,
    position_value,
    resolve_day_start_bankroll,
    should_halt_for_loss,
    unheld_markets,
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


class FakeClient:
    def __init__(self, positions, markets):
        self.positions = positions
        self.markets = markets

    def get_positions(self, *, cursor=None):
        return {"market_positions": self.positions, "cursor": ""}

    def get_market(self, ticker):
        return self.markets[ticker]


def _market(ticker):
    return Market(
        ticker=ticker,
        event_ticker="EV",
        title=ticker,
        yes_bid=Decimal("0.40"),
        yes_ask=Decimal("0.42"),
        volume_24h=Decimal("100"),
        liquidity=Decimal("0"),
        close_time="",
        rules_primary="",
        category="",
        subtitle="",
    )


def test_skips_ticker_with_existing_position():
    client = FakeClient(
        [
            {"ticker": "HELD", "position_fp": "5.00"},
            {"ticker": "FLAT", "position_fp": "0.00"},
        ],
        {},
    )
    held = open_positions(client)
    assert set(held) == {"HELD"}
    markets = [_market("HELD"), _market("FLAT"), _market("NEW")]
    assert [m.ticker for m in unheld_markets(markets, held)] == ["FLAT", "NEW"]


def _equity(cash, positions, markets):
    client = FakeClient(positions, markets)
    return cash + positions_value(client, open_positions(client))


def test_buying_contracts_is_not_a_daily_loss():
    start = _equity(Decimal("100"), [], {})
    after_buy = _equity(
        Decimal("60"),
        [{"ticker": "A", "position_fp": "100", "market_exposure_dollars": "40"}],
        {"A": {"yes_bid_dollars": "0.3900", "yes_ask_dollars": "0.4100"}},
    )
    assert after_buy == Decimal("100")
    assert should_halt_for_loss(start, after_buy, 0.10) is False
    assert should_halt_for_loss(start, Decimal("60"), 0.10) is True


def test_mark_to_market_drop_is_a_daily_loss():
    start = Decimal("100")
    dropped = _equity(
        Decimal("60"),
        [{"ticker": "A", "position_fp": "100", "market_exposure_dollars": "40"}],
        {"A": {"yes_bid_dollars": "0.2900", "yes_ask_dollars": "0.3100"}},
    )
    assert dropped == Decimal("90")
    assert should_halt_for_loss(start, dropped, 0.10) is True


def test_no_position_valued_against_yes_price():
    value = position_value(
        Decimal("-10"), Decimal("6"), Decimal("0.39"), Decimal("0.41")
    )
    assert value == Decimal("6.00")


def test_position_without_quotes_falls_back_to_cost():
    value = position_value(Decimal("10"), Decimal("4"), Decimal("0"), Decimal("0"))
    assert value == Decimal("4")


def test_kalshi_fee_rounds_up_to_cent():
    assert kalshi_fee(1, Decimal("0.50")) == Decimal("0.02")
    assert kalshi_fee(100, Decimal("0.50")) == Decimal("1.75")
    assert kalshi_fee(10, Decimal("0.30")) == Decimal("0.15")
    assert kalshi_fee(1, Decimal("0.99")) == Decimal("0.01")


def test_fee_adjusted_edge():
    assert abs(fee_adjusted_edge(0.6, Decimal("0.50")) - 0.08) < 1e-9
    assert abs(fee_adjusted_edge(0.6, Decimal("0.50"), 100) - 0.0825) < 1e-9
    assert fee_adjusted_edge(0.51, Decimal("0.50")) < 0
