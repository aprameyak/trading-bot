from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN

from bot.brain import TradeIdea
from bot.config import Settings


@dataclass
class SizedTrade:
    idea: TradeIdea
    contracts: int
    side: str
    price: Decimal
    cost: Decimal
    kelly: float


def _floor_contracts(n: Decimal) -> int:
    return max(0, int(n.to_integral_value(rounding=ROUND_DOWN)))


def kelly_fraction(p: float, price: float) -> float:
    if price <= 0 or price >= 1:
        return 0.0
    edge = p - price
    if edge <= 0:
        return 0.0
    return edge / (1.0 - price)


def size_trade(
    idea: TradeIdea,
    bankroll: Decimal,
    settings: Settings,
    reserved: Decimal = Decimal("0"),
) -> SizedTrade | None:
    market = idea.market
    if not market or not idea.should_trade:
        return None

    available = bankroll - reserved
    if available <= Decimal("0.01"):
        return None

    if idea.action == "buy_yes":
        side = "bid"
        exec_price = market.yes_ask
        contract_cost = market.yes_ask
        p = idea.fair_yes_prob
    else:
        if market.yes_bid <= 0:
            return None
        side = "ask"
        exec_price = market.yes_bid
        contract_cost = Decimal("1") - market.yes_bid
        p = 1.0 - idea.fair_yes_prob

    if contract_cost <= 0 or contract_cost >= 1:
        return None

    k = (
        kelly_fraction(p, float(contract_cost))
        * settings.kelly_fraction
        * idea.confidence
    )
    k = min(k, settings.max_position_fraction)
    if k <= 0:
        return None

    stake = available * Decimal(str(k))
    contracts = _floor_contracts(stake / contract_cost)
    if contracts < 1:
        return None

    return SizedTrade(
        idea=idea,
        contracts=contracts,
        side=side,
        price=exec_price,
        cost=Decimal(contracts) * contract_cost,
        kelly=k,
    )


def size_ideas(
    ideas: list[TradeIdea],
    bankroll: Decimal,
    settings: Settings,
) -> list[SizedTrade]:
    sized: list[SizedTrade] = []
    reserved = Decimal("0")
    cycle_cap = bankroll * Decimal(str(settings.max_position_fraction)) * 3
    for idea in ideas:
        trade = size_trade(idea, bankroll, settings, reserved=reserved)
        if not trade:
            continue
        sized.append(trade)
        reserved += trade.cost
        if reserved >= cycle_cap:
            break
    return sized
