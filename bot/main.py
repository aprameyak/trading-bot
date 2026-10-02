from __future__ import annotations

import time
import traceback
from decimal import Decimal

from rich.console import Console
from rich.table import Table

from bot.brain import Brain
from bot.config import Settings
from bot.executor import Executor, balance_dollars
from bot.kalshi_client import KalshiClient
from bot.risk import size_ideas
from bot.scanner import scan_markets
from bot.store import TradeLog

console = Console()


def _print_ideas(ideas) -> None:
    table = Table(title="Claude trade ideas")
    table.add_column("Ticker")
    table.add_column("Action")
    table.add_column("Fair YES")
    table.add_column("Edge")
    table.add_column("Conf")
    table.add_column("Why")
    for idea in ideas:
        table.add_row(
            idea.ticker,
            idea.action,
            f"{idea.fair_yes_prob:.1%}",
            f"{idea.edge:.1%}",
            f"{idea.confidence:.0%}",
            idea.rationale[:60],
        )
    console.print(table)


def run_cycle(settings: Settings) -> None:
    settings.validate()
    client = KalshiClient(
        settings.kalshi_base_url,
        settings.kalshi_api_key_id,
        settings.kalshi_private_key_path,
    )
    log = TradeLog(settings.data_dir / "trades.sqlite3")
    brain = Brain(settings)
    executor = Executor(client, settings, log)

    bankroll = balance_dollars(client)
    console.print(
        f"[bold]Cycle[/bold] env={settings.kalshi_env} dry_run={settings.dry_run} "
        f"bankroll=${bankroll}"
    )

    markets = scan_markets(client, settings)
    console.print(f"Scanning {len(markets)} liquid markets…")
    if not markets:
        console.print("[dim]No markets passed filters this cycle.[/dim]")
        return

    ideas = brain.evaluate(markets, bankroll)
    _print_ideas(ideas)

    trades = size_ideas(ideas, bankroll, settings)
    if not trades:
        console.print("[dim]No actionable edges after sizing filters.[/dim]")
        return

    reserved = Decimal("0")
    for trade in trades:
        try:
            live = executor.prepare(trade, bankroll, reserved)
            if not live:
                continue
            executor.execute(live)
            reserved += live.cost
        except Exception as exc:
            console.print(f"[red]Order failed for {trade.idea.ticker}: {exc}[/red]")


def main() -> None:
    settings = Settings.from_env()
    console.print(
        "[bold cyan]Kalshi profit bot[/bold cyan]\n"
        f"Env: {settings.kalshi_env} | Dry-run: {settings.dry_run} | "
        f"Model: {settings.anthropic_model}"
    )
    if settings.kalshi_env == "prod" and not settings.dry_run:
        if settings.confirm_live != "I_UNDERSTAND":
            raise SystemExit(
                "Refusing live prod. Set CONFIRM_LIVE=I_UNDERSTAND to continue."
            )
        console.print(
            "[bold red]LIVE PRODUCTION MODE[/bold red] — real money will be risked."
        )

    while True:
        try:
            run_cycle(settings)
        except KeyboardInterrupt:
            console.print("\nStopped.")
            return
        except Exception:
            console.print("[red]Cycle error:[/red]")
            console.print(traceback.format_exc())
        console.print(f"Sleeping {settings.poll_interval_seconds}s…")
        try:
            time.sleep(settings.poll_interval_seconds)
        except KeyboardInterrupt:
            console.print("\nStopped.")
            return


if __name__ == "__main__":
    main()
