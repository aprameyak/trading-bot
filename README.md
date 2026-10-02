# Kalshi Local Trading Bot

Local auto-trader: scans Kalshi, estimates odds with Claude, sizes with Kelly, places orders. Defaults to demo + dry-run.

## Disclaimer

Not financial advice. You can lose money. LLM probability estimates are not trading edge. Defaults are aggressive (`KELLY_FRACTION=0.75`, `AGGRESSIVE_TAKER=true`) and intended for dry-run experimentation only. Keep `DRY_RUN=true` until you understand the risk model.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

1. Set `ANTHROPIC_API_KEY` in `.env`
2. Create a demo API key at https://demo.kalshi.co → Profile → API Keys
3. Save the PEM as `keys/kalshi.pem` and set `KALSHI_API_KEY_ID`

Never commit PEM files or `.env`.

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

## License

MIT
