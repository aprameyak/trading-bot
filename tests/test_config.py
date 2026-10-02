from pathlib import Path

from bot.config import Settings


def _settings(**overrides) -> Settings:
    base = dict(
        kalshi_env="demo",
        kalshi_base_url="https://example.test",
        kalshi_api_key_id="key",
        kalshi_private_key_path=Path("/tmp/missing-key.pem"),
        anthropic_api_key="sk-test",
        anthropic_model="claude-haiku-4-5",
        dry_run=True,
        poll_interval_seconds=90,
        max_markets_per_cycle=12,
        min_volume_24h=50.0,
        min_edge=0.06,
        min_confidence=0.55,
        kelly_fraction=0.25,
        max_position_fraction=0.10,
        max_hours_to_close=720.0,
        aggressive_taker=False,
        confirm_live="",
        max_daily_loss_fraction=0.10,
        data_dir=Path("/tmp"),
    )
    base.update(overrides)
    return Settings(**base)


def test_safer_defaults_match_public_contract(monkeypatch):
    for key in (
        "KALSHI_ENV",
        "DRY_RUN",
        "KELLY_FRACTION",
        "MAX_POSITION_FRACTION",
        "AGGRESSIVE_TAKER",
        "CONFIRM_LIVE",
        "MAX_DAILY_LOSS_FRACTION",
    ):
        monkeypatch.delenv(key, raising=False)
    s = Settings.from_env()
    assert s.kalshi_env == "demo"
    assert s.dry_run is True
    assert s.kelly_fraction == 0.25
    assert s.max_position_fraction == 0.10
    assert s.aggressive_taker is False
    assert s.confirm_live == ""
    assert s.max_daily_loss_fraction == 0.10


def test_confirm_live_required_for_live_prod(tmp_path: Path):
    key = tmp_path / "kalshi.pem"
    key.write_text("placeholder")
    s = _settings(
        kalshi_env="prod",
        dry_run=False,
        confirm_live="",
        kalshi_private_key_path=key,
    )
    try:
        s.validate()
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "CONFIRM_LIVE=I_UNDERSTAND" in str(exc)


def test_confirm_live_accepted_for_live_prod(tmp_path: Path):
    key = tmp_path / "kalshi.pem"
    key.write_text("placeholder")
    s = _settings(
        kalshi_env="prod",
        dry_run=False,
        confirm_live="I_UNDERSTAND",
        kalshi_private_key_path=key,
    )
    s.validate()


def test_max_daily_loss_fraction_bounds(tmp_path: Path):
    key = tmp_path / "kalshi.pem"
    key.write_text("placeholder")
    for bad in (0.0, -0.1, 1.01):
        s = _settings(
            max_daily_loss_fraction=bad,
            kalshi_private_key_path=key,
        )
        try:
            s.validate()
            assert False, f"expected ValueError for {bad}"
        except ValueError as exc:
            assert "MAX_DAILY_LOSS_FRACTION" in str(exc)
