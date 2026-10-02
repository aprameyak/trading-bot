# Kalshi local trading bot

Claude estimates odds; Kelly sizes; Kalshi places. Defaults: demo + dry-run.

Not financial advice. Live prod requires `CONFIRM_LIVE=I_UNDERSTAND`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `ANTHROPIC_API_KEY`, demo key id, PEM at `keys/kalshi.pem`.

```bash
python check_setup.py
python run.py
```

| Var | Default |
| --- | --- |
| `DRY_RUN` | `true` |
| `KELLY_FRACTION` | `0.25` |
| `MAX_POSITION_FRACTION` | `0.10` |
| `AGGRESSIVE_TAKER` | `false` |
| `CONFIRM_LIVE` | empty |

## License

MIT
