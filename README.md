# trading-bot

A local Python bot that trades Kalshi binary markets. It asks Claude to estimate the probability of each market resolving YES, compares that to the current price after fees, and sizes any entries with fractional Kelly. By default it runs against Kalshi's demo environment in dry-run mode.

Not financial advice. Prediction markets can lose money, and Claude's probability estimates can be wrong. Start on demo with `DRY_RUN=true`, and read the code before risking real funds.

## Safety defaults

- `KALSHI_ENV=demo` and `DRY_RUN=true` out of the box. In dry-run mode, orders are printed and logged but never sent.
- Real-money orders require all three of `KALSHI_ENV=prod`, `DRY_RUN=false`, and `CONFIRM_LIVE=I_UNDERSTAND`. Without the confirmation, the bot refuses to start.
- Trading halts when equity (cash plus marked position value) falls by `MAX_DAILY_LOSS_FRACTION` from the start of the UTC day.
- Each position is capped at `MAX_POSITION_FRACTION` of the bankroll, and each cycle spends at most three times that.
- Entries only. The bot does not sell or close positions, and it skips markets where you already hold a position.

## Features

- Scans open Kalshi events, filters by 24h volume, spread, and time to close, and ranks the best candidates.
- Sends the shortlisted markets to Claude, which returns `buy_yes`, `buy_no`, or `skip` with a fair probability, confidence, and one-line rationale.
- Computes edge net of Kalshi's trading fee and drops ideas below `MIN_EDGE` or `MIN_CONFIDENCE`.
- Re-fetches each market right before ordering and re-sizes, skipping the trade if the edge has shrunk.
- Records every decision (dry-run or live) in a local SQLite file at `data/trades.sqlite3`.

## Tech stack

- Python 3 (CI uses 3.12)
- `anthropic` SDK for Claude
- `requests` and `cryptography` for the Kalshi REST API with RSA-PSS request signing
- `rich` for terminal output, `python-dotenv` for config, `pytest` for tests

## Getting started

Prerequisites: Python 3, an Anthropic API key, and a Kalshi API key (demo account recommended) with its private key PEM file.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env` and place your Kalshi private key at `keys/kalshi.pem` (or set `KALSHI_PRIVATE_KEY_PATH`). `keys/*` and `*.pem` are gitignored.

Required:

- `ANTHROPIC_API_KEY`
- `KALSHI_API_KEY_ID`
- `KALSHI_PRIVATE_KEY_PATH`

Optional, with defaults in `.env.example`:

- `KALSHI_ENV` (`demo` or `prod`), `ANTHROPIC_MODEL`, `DRY_RUN`, `CONFIRM_LIVE`
- `POLL_INTERVAL_SECONDS`, `MAX_MARKETS_PER_CYCLE`, `MIN_VOLUME_24H`, `MAX_HOURS_TO_CLOSE`
- `MIN_EDGE`, `MIN_CONFIDENCE`, `KELLY_FRACTION`, `MAX_POSITION_FRACTION`, `MAX_DAILY_LOSS_FRACTION`
- `AGGRESSIVE_TAKER`: when true, orders are fill-or-kill instead of good-till-canceled

Check credentials and the scanner, then start the loop:

```bash
python check_setup.py
python run.py
```

`run.py` runs one cycle every `POLL_INTERVAL_SECONDS` until you press Ctrl+C.

Run the tests:

```bash
PYTHONPATH=. pytest -q
```

## How it works

Each cycle in `bot/main.py`:

1. `bot/executor.py` reads the balance and open positions; `bot/risk.py` checks the daily drawdown limit against a baseline stored in `bot/store.py`.
2. `bot/scanner.py` pages through Kalshi events and returns the top `MAX_MARKETS_PER_CYCLE` liquid markets you do not already hold.
3. `bot/brain.py` sends them to Claude and parses the JSON array of trade ideas.
4. `bot/risk.py` sizes each idea: Kelly fraction times `KELLY_FRACTION` times confidence, capped at `MAX_POSITION_FRACTION`.
5. `bot/executor.py` refreshes the market, re-checks edge, and either logs a dry run or places a limit order through `bot/kalshi_client.py`.

Settings and their validation live in `bot/config.py`.

## Contributing

Issues and pull requests are welcome. Run `PYTHONPATH=. pytest -q` before opening a PR; CI runs the same command on every push and pull request.

## License

MIT. See [LICENSE](LICENSE).
