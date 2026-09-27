# Kalshi Local Profit Bot

Local auto-trader: scans Kalshi, estimates odds with Claude, sizes with Kelly, places orders. Defaults to demo + dry-run.

## Setup

```bash
cd trading-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

1. Set `ANTHROPIC_API_KEY` in `.env`
2. Create a demo API key at https://demo.kalshi.co → Profile → API Keys
3. Save the PEM as `keys/kalshi.pem` and set `KALSHI_API_KEY_ID`

```bash
python check_setup.py
python run.py
```

## Go live

1. Demo with `DRY_RUN=false` until fills look right
2. Production key from https://kalshi.com, then:

```
KALSHI_ENV=prod
KALSHI_API_KEY_ID=...
KALSHI_PRIVATE_KEY_PATH=keys/kalshi-prod.pem
DRY_RUN=false
```

## Config

| Var | Default |
| --- | --- |
| `DRY_RUN` | `true` |
| `MIN_EDGE` | `0.06` |
| `MIN_CONFIDENCE` | `0.55` |
| `KELLY_FRACTION` | `0.75` |
| `MAX_POSITION_FRACTION` | `0.35` |
| `MAX_HOURS_TO_CLOSE` | `720` |
| `POLL_INTERVAL_SECONDS` | `90` |
| `AGGRESSIVE_TAKER` | `true` |

Decisions log to `data/trades.sqlite3`. Keep the process running locally (Terminal or tmux).
