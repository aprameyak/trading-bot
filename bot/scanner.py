from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from bot.config import Settings
from bot.kalshi_client import KalshiClient, Market, _d


def _parse_close(close_time: str) -> datetime | None:
    if not close_time:
        return None
    try:
        return datetime.fromisoformat(close_time.replace("Z", "+00:00"))
    except ValueError:
        return None


def hours_to_close(close_time: str) -> float | None:
    dt = _parse_close(close_time)
    if not dt:
        return None
    return (dt - datetime.now(timezone.utc)).total_seconds() / 3600.0


def market_from_raw(raw: dict, category: str = "", event_title: str = "") -> Market | None:
    if raw.get("mve_collection_ticker") or raw.get("mve_selected_legs"):
        return None
    status = (raw.get("status") or "").lower()
    if status not in {"open", "active"}:
        return None

    yes_bid = _d(raw.get("yes_bid_dollars"))
    yes_ask = _d(raw.get("yes_ask_dollars"))
    if yes_ask <= 0 or yes_ask >= 1:
        return None
    if yes_bid < 0:
        yes_bid = Decimal("0")
    if yes_bid >= yes_ask:
        return None

    title = raw.get("title") or event_title or raw.get("yes_sub_title") or raw.get("ticker")
    return Market(
        ticker=raw["ticker"],
        event_ticker=raw.get("event_ticker") or "",
        title=title,
        yes_bid=yes_bid,
        yes_ask=yes_ask,
        volume_24h=_d(raw.get("volume_24h_fp") or raw.get("volume_fp")),
        liquidity=_d(raw.get("liquidity_dollars")),
        close_time=raw.get("close_time") or raw.get("expected_expiration_time") or "",
        rules_primary=(raw.get("rules_primary") or "")[:800],
        category=category or raw.get("category") or "",
        subtitle=raw.get("yes_sub_title") or raw.get("no_sub_title") or "",
    )


def score_market(m: Market, settings: Settings) -> float:
    hrs = hours_to_close(m.close_time)
    if hrs is not None and hrs <= 0:
        return -1.0
    if (
        settings.max_hours_to_close > 0
        and hrs is not None
        and hrs > settings.max_hours_to_close
    ):
        return -1.0
    if m.volume_24h < Decimal(str(settings.min_volume_24h)):
        return -1.0

    spread = float(m.spread) if m.yes_bid > 0 else float(m.yes_ask)
    if spread > 0.25:
        return -1.0

    mid = float(m.mid)
    extremity = abs(mid - 0.5)
    vol = float(m.volume_24h)
    urgency = 0.35
    if hrs is not None and settings.max_hours_to_close > 0:
        urgency = max(0.15, 1.0 - (hrs / settings.max_hours_to_close))
    elif hrs is not None:
        urgency = max(0.1, 1.0 - min(hrs, 24 * 365) / (24 * 90))
    return (vol**0.5) * (1.0 - min(spread, 0.5)) * (1.0 - 0.35 * extremity) * (
        0.4 + urgency
    )


def scan_markets(client: KalshiClient, settings: Settings) -> list[Market]:
    candidates: list[Market] = []
    cursor = None
    pages = 0
    max_pages = 25
    target_pool = max(settings.max_markets_per_cycle * 8, 40)

    while pages < max_pages and len(candidates) < target_pool:
        data = client.list_events(limit=200, cursor=cursor)
        pages += 1
        for event in data.get("events") or []:
            category = event.get("category") or ""
            event_title = event.get("title") or ""
            for raw in event.get("markets") or []:
                m = market_from_raw(raw, category=category, event_title=event_title)
                if m and score_market(m, settings) >= 0:
                    candidates.append(m)
        cursor = data.get("cursor")
        if not cursor:
            break

    best: dict[str, tuple[float, Market]] = {}
    for m in candidates:
        s = score_market(m, settings)
        prev = best.get(m.ticker)
        if prev is None or s > prev[0]:
            best[m.ticker] = (s, m)

    ranked = sorted(best.values(), key=lambda x: x[0], reverse=True)
    return [m for _, m in ranked[: settings.max_markets_per_cycle]]


def refresh_market(client: KalshiClient, market: Market) -> Market | None:
    raw = client.get_market(market.ticker)
    if not raw:
        return None
    return market_from_raw(
        raw,
        category=market.category,
        event_title=market.title,
    )
