#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rich.console import Console

from bot.config import Settings
from bot.executor import balance_dollars
from bot.kalshi_client import KalshiClient
from bot.scanner import scan_markets

console = Console()


def main() -> int:
    settings = Settings.from_env()
    missing = []
    if not settings.anthropic_api_key:
        missing.append("ANTHROPIC_API_KEY")
    if not settings.kalshi_api_key_id:
        missing.append("KALSHI_API_KEY_ID")
    if not settings.kalshi_private_key_path.exists():
        missing.append(f"key file {settings.kalshi_private_key_path}")
    if missing:
        console.print(f"[red]Missing:[/red] {', '.join(missing)}")
        console.print("Copy .env.example → .env and add keys (see README).")
        return 1

    try:
        settings.validate()
    except ValueError as exc:
        console.print(f"[red]Config error:[/red] {exc}")
        return 1

    client = KalshiClient(
        settings.kalshi_base_url,
        settings.kalshi_api_key_id,
        settings.kalshi_private_key_path,
    )
    try:
        bal = balance_dollars(client)
    except Exception as exc:
        console.print(f"[red]Kalshi auth failed:[/red] {exc}")
        return 1

    console.print(
        f"[green]Kalshi auth OK[/green] ({settings.kalshi_env}) balance=${bal}"
    )

    markets = scan_markets(client, settings)
    console.print(f"Scanner found {len(markets)} candidate markets")
    for m in markets[:5]:
        console.print(f"  {m.ticker}  {m.yes_bid}/{m.yes_ask}  {m.title[:70]}")
    console.print("[green]Setup looks good.[/green] Run: python run.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
