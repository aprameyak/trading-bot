from __future__ import annotations

from decimal import Decimal

from rich.console import Console

from bot.brain import TradeIdea
from bot.config import Settings
from bot.kalshi_client import KalshiClient, _d
from bot.risk import (
    SizedTrade,
    fee_adjusted_edge,
    position_value,
    size_trade,
)
from bot.scanner import refresh_market
from bot.store import TradeLog

console = Console()


class Executor:
    def __init__(self, client: KalshiClient, settings: Settings, log: TradeLog):
        self.client = client
        self.settings = settings
        self.log = log

    def prepare(self, trade: SizedTrade, bankroll: Decimal, reserved: Decimal) -> SizedTrade | None:
        fresh = refresh_market(self.client, trade.idea.market)
        if not fresh:
            console.print(f"[dim]Skip {trade.idea.ticker}: market vanished[/dim]")
            return None

        idea = TradeIdea(
            ticker=trade.idea.ticker,
            action=trade.idea.action,
            fair_yes_prob=trade.idea.fair_yes_prob,
            confidence=trade.idea.confidence,
            edge=trade.idea.edge,
            rationale=trade.idea.rationale,
            market=fresh,
        )
        if idea.action == "buy_yes":
            idea.edge = fee_adjusted_edge(idea.fair_yes_prob, fresh.yes_ask)
        else:
            if fresh.yes_bid <= 0:
                console.print(f"[dim]Skip {idea.ticker}: no usable NO ask[/dim]")
                return None
            idea.edge = fee_adjusted_edge(
                1.0 - idea.fair_yes_prob, Decimal("1") - fresh.yes_bid
            )

        if idea.edge < self.settings.min_edge:
            console.print(
                f"[dim]Skip {idea.ticker}: edge shrunk to {idea.edge:.1%} after refresh[/dim]"
            )
            return None

        resized = size_trade(idea, bankroll, self.settings, reserved=reserved)
        if not resized:
            console.print(f"[dim]Skip {idea.ticker}: cannot size after refresh[/dim]")
            return None
        return resized

    def execute(self, trade: SizedTrade) -> dict | None:
        idea = trade.idea
        tif = "fill_or_kill" if self.settings.aggressive_taker else "good_till_canceled"
        payload = {
            "ticker": idea.ticker,
            "action": idea.action,
            "side": trade.side,
            "contracts": trade.contracts,
            "price": str(trade.price),
            "cost": str(trade.cost),
            "edge": idea.edge,
            "confidence": idea.confidence,
            "kelly": trade.kelly,
            "rationale": idea.rationale,
            "time_in_force": tif,
        }

        if self.settings.dry_run:
            console.print(
                f"[yellow]DRY-RUN[/yellow] {idea.action} {trade.contracts}x "
                f"{idea.ticker} @ {trade.price} (side={trade.side}, edge={idea.edge:.1%})"
            )
            console.print(f"  {idea.rationale}")
            self.log.record(dry_run=True, payload=payload, result={"status": "dry_run"})
            return {"status": "dry_run"}

        result = self.client.create_order(
            ticker=idea.ticker,
            side=trade.side,
            count=trade.contracts,
            price=trade.price,
            time_in_force=tif,
            post_only=False,
        )
        console.print(
            f"[green]ORDER[/green] {idea.action} {trade.contracts}x {idea.ticker} "
            f"@ {trade.price} → {result.get('order_id') or result}"
        )
        self.log.record(dry_run=False, payload=payload, result=result)
        return result


def balance_dollars(client: KalshiClient) -> Decimal:
    bal = client.get_balance()
    if bal.get("balance_dollars") is not None:
        return Decimal(str(bal["balance_dollars"]))
    return Decimal(bal.get("balance", 0)) / Decimal(100)


def open_positions(client: KalshiClient) -> dict[str, dict]:
    held: dict[str, dict] = {}
    cursor = None
    while True:
        data = client.get_positions(cursor=cursor)
        for pos in data.get("market_positions") or []:
            if _d(pos.get("position_fp")) != 0:
                held[pos["ticker"]] = pos
        cursor = data.get("cursor")
        if not cursor:
            return held


def positions_value(client: KalshiClient, positions: dict[str, dict]) -> Decimal:
    total = Decimal("0")
    for ticker, pos in positions.items():
        raw = client.get_market(ticker)
        total += position_value(
            _d(pos.get("position_fp")),
            _d(pos.get("market_exposure_dollars")),
            _d(raw.get("yes_bid_dollars")),
            _d(raw.get("yes_ask_dollars")),
        )
    return total
