from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

ENV_URLS = {
    "demo": "https://external-api.demo.kalshi.co/trade-api/v2",
    "prod": "https://external-api.kalshi.com/trade-api/v2",
}


@dataclass(frozen=True)
class Settings:
    kalshi_env: str
    kalshi_base_url: str
    kalshi_api_key_id: str
    kalshi_private_key_path: Path
    anthropic_api_key: str
    anthropic_model: str
    dry_run: bool
    poll_interval_seconds: int
    max_markets_per_cycle: int
    min_volume_24h: float
    min_edge: float
    min_confidence: float
    kelly_fraction: float
    max_position_fraction: float
    max_hours_to_close: float
    aggressive_taker: bool
    data_dir: Path

    @classmethod
    def from_env(cls) -> Settings:
        env = os.getenv("KALSHI_ENV", "demo").strip().lower()
        if env not in ENV_URLS:
            raise ValueError(f"KALSHI_ENV must be demo or prod, got {env!r}")

        key_path = Path(
            os.getenv("KALSHI_PRIVATE_KEY_PATH", "keys/kalshi.pem")
        ).expanduser()
        if not key_path.is_absolute():
            key_path = ROOT / key_path

        return cls(
            kalshi_env=env,
            kalshi_base_url=ENV_URLS[env],
            kalshi_api_key_id=os.getenv("KALSHI_API_KEY_ID", "").strip(),
            kalshi_private_key_path=key_path,
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5").strip(),
            dry_run=os.getenv("DRY_RUN", "true").strip().lower()
            in {"1", "true", "yes"},
            poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "90")),
            max_markets_per_cycle=int(os.getenv("MAX_MARKETS_PER_CYCLE", "12")),
            min_volume_24h=float(os.getenv("MIN_VOLUME_24H", "50")),
            min_edge=float(os.getenv("MIN_EDGE", "0.06")),
            min_confidence=float(os.getenv("MIN_CONFIDENCE", "0.55")),
            kelly_fraction=float(os.getenv("KELLY_FRACTION", "0.75")),
            max_position_fraction=float(os.getenv("MAX_POSITION_FRACTION", "0.35")),
            max_hours_to_close=float(os.getenv("MAX_HOURS_TO_CLOSE", "720")),
            aggressive_taker=os.getenv("AGGRESSIVE_TAKER", "true").strip().lower()
            in {"1", "true", "yes"},
            data_dir=ROOT / "data",
        )

    def validate(self) -> None:
        if not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")
        if not self.kalshi_api_key_id:
            raise ValueError("KALSHI_API_KEY_ID is required")
        if not self.kalshi_private_key_path.exists():
            raise ValueError(
                f"Kalshi private key not found at {self.kalshi_private_key_path}"
            )
        if self.kelly_fraction <= 0 or self.max_position_fraction <= 0:
            raise ValueError("KELLY_FRACTION and MAX_POSITION_FRACTION must be > 0")
        if self.min_edge < 0 or self.min_confidence < 0:
            raise ValueError("MIN_EDGE and MIN_CONFIDENCE must be >= 0")
