# Kalshi local trading bot

Scans Kalshi markets, estimates odds with Claude, sizes with Kelly, places orders. Defaults: demo API + `DRY_RUN=true`.

## Warning

Not financial advice. You can lose money. Model estimates are not edge. Defaults are conservative (`KELLY_FRACTION=0.25`, `AGGRESSIVE_TAKER=false`). Live prod also requires `CONFIRM_LIVE=I_UNDERSTAND`.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

1. Set `ANTHROPIC_API_KEY`
2. Demo API key from https://demo.kalshi.co → Profile → API Keys
3. Save PEM as `keys/kalshi.pem` and set `KALSHI_API_KEY_ID`

Do not commit PEMs or `.env`.

```bash
python check_setup.py
python run.py
```

## Live

1. Demo with `DRY_RUN=false` until fills look right
2. Prod key from https://kalshi.com:

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
| `KELLY_FRACTION` | `0.25` |
| `MAX_POSITION_FRACTION` | `0.10` |
| `MAX_HOURS_TO_CLOSE` | `720` |
| `POLL_INTERVAL_SECONDS` | `90` |
| `AGGRESSIVE_TAKER` | `false` |
| `CONFIRM_LIVE` | empty (required `I_UNDERSTAND` for live prod) |

Logs to `data/trades.sqlite3`.

## License

MIT
