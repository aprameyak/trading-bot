from __future__ import annotations

import json
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from anthropic import Anthropic

from bot.config import Settings
from bot.kalshi_client import Market


@dataclass
class TradeIdea:
    ticker: str
    action: str
    fair_yes_prob: float
    confidence: float
    edge: float
    rationale: str
    market: Market | None = None

    @property
    def should_trade(self) -> bool:
        return self.action in {"buy_yes", "buy_no"} and self.edge > 0


SYSTEM_PROMPT = """You are a rational prediction-market trader for Kalshi binary contracts.
Your objective is expected-value profit within stated risk limits.

Rules:
- Estimate the true probability that YES resolves to $1.
- Compare fair probability to the executable price (buy YES at yes_ask, buy NO at 1 - yes_bid).
- Only recommend a trade when there is a clear positive edge after spread.
- Prefer higher-confidence, nearer-resolution, liquid markets.
- Be honest when the market looks efficient — skip is a valid and common answer.
- Do not invent news you do not know. Use general knowledge and the market text only.
- Never suggest both sides. Never suggest selling an existing position here (entries only).
- If yes_bid is 0, do not recommend buy_no.

Respond with ONLY a JSON array. Each element:
{
  "ticker": "...",
  "action": "buy_yes" | "buy_no" | "skip",
  "fair_yes_prob": 0.0-1.0,
  "confidence": 0.0-1.0,
  "rationale": "one short sentence"
}
"""


def _extract_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            raise
        return json.loads(match.group(0))


def _edge_for(action: str, fair: float, market: Market) -> float:
    if action == "buy_yes":
        return fair - float(market.yes_ask)
    if action == "buy_no":
        if market.yes_bid <= 0:
            return -1.0
        no_ask = 1.0 - float(market.yes_bid)
        return (1.0 - fair) - no_ask
    return 0.0


class Brain:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = Anthropic(api_key=settings.anthropic_api_key)

    def evaluate(self, markets: list[Market], bankroll: Decimal) -> list[TradeIdea]:
        if not markets:
            return []

        payload = {
            "bankroll_usd": float(bankroll),
            "min_edge": self.settings.min_edge,
            "goal": "maximize expected profit within risk limits",
            "markets": [
                {
                    "ticker": m.ticker,
                    "title": m.title,
                    "category": m.category,
                    "subtitle": m.subtitle,
                    "yes_bid": float(m.yes_bid),
                    "yes_ask": float(m.yes_ask),
                    "mid": float(m.mid),
                    "spread": float(m.spread),
                    "volume_24h": float(m.volume_24h),
                    "close_time": m.close_time,
                    "rules": m.rules_primary,
                }
                for m in markets
            ],
        }

        msg = self.client.messages.create(
            model=self.settings.anthropic_model,
            max_tokens=2500,
            temperature=0.2,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Evaluate these Kalshi markets and return trade ideas as JSON.\n"
                        + json.dumps(payload, indent=2)
                    ),
                }
            ],
        )
        text = "".join(block.text for block in msg.content if hasattr(block, "text"))
        raw_ideas = _extract_json(text)
        if not isinstance(raw_ideas, list):
            raise ValueError("Claude did not return a JSON array")

        by_ticker = {m.ticker: m for m in markets}
        ideas: list[TradeIdea] = []
        for item in raw_ideas:
            if not isinstance(item, dict):
                continue
            ticker = str(item.get("ticker", ""))
            market = by_ticker.get(ticker)
            if not market:
                continue
            action = str(item.get("action", "skip")).lower().strip()
            if action not in {"buy_yes", "buy_no", "skip"}:
                action = "skip"
            try:
                fair = float(item.get("fair_yes_prob", 0.5))
                confidence = float(item.get("confidence", 0.0))
            except (TypeError, ValueError):
                continue
            fair = min(max(fair, 0.01), 0.99)
            confidence = min(max(confidence, 0.0), 1.0)
            edge = _edge_for(action, fair, market)
            if action == "buy_no" and market.yes_bid <= 0:
                action = "skip"
                edge = 0.0
            if action != "skip" and (
                edge < self.settings.min_edge
                or confidence < self.settings.min_confidence
            ):
                action = "skip"
                edge = 0.0
            ideas.append(
                TradeIdea(
                    ticker=ticker,
                    action=action,
                    fair_yes_prob=fair,
                    confidence=confidence,
                    edge=max(edge, 0.0) if action == "skip" else edge,
                    rationale=str(item.get("rationale", ""))[:280],
                    market=market,
                )
            )
        ideas.sort(key=lambda x: x.edge * x.confidence, reverse=True)
        return ideas
