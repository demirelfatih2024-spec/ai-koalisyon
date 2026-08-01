"""Central configuration, loaded from .env with documented defaults.

Nothing secret is ever hard-coded here; credentials come from the environment.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent

load_dotenv(PROJECT_ROOT / ".env")

# OKX keeps only the trailing 3 months of positions-history and orders-algo-history.
# Anything older simply does not exist over the API and must come from a UI export.
API_HISTORY_RETENTION_DAYS = 90


def _f(name: str, default: float) -> float:
    raw = os.getenv(name)
    return default if raw is None or raw == "" else float(raw)


def _i(name: str, default: int) -> int:
    raw = os.getenv(name)
    return default if raw is None or raw == "" else int(raw)


def _s(name: str, default: str) -> str:
    raw = os.getenv(name)
    return default if raw is None or raw == "" else raw


@dataclass(frozen=True)
class Credentials:
    api_key: str
    api_secret: str
    passphrase: str
    simulated: bool = False

    @property
    def is_complete(self) -> bool:
        return bool(self.api_key and self.api_secret and self.passphrase)


@dataclass(frozen=True)
class ExtensionWindowConfig:
    """Adaptive post-close observation window.

    We always watch at least ``min_hours``. After that we keep extending while the
    trade keeps making new favourable extremes, and stop once price gives back
    ``retrace_atr_mult`` * ATR from the running peak, or ``max_hours`` elapses.
    """

    min_hours: float = 4.0
    max_hours: float = 72.0
    retrace_atr_mult: float = 1.5
    retrace_pct_fallback: float = 0.015
    retrace_basis: str = "close"  # 'close' | 'extreme'

    def __post_init__(self) -> None:
        if self.retrace_basis not in ("close", "extreme"):
            raise ValueError("retrace_basis must be 'close' or 'extreme'")
        if self.min_hours > self.max_hours:
            raise ValueError("min_hours cannot exceed max_hours")


@dataclass(frozen=True)
class MatchConfig:
    """Tolerances for deciding that a close price 'is' a TP/SL trigger price."""

    tick_tolerance: float = 8.0
    pct_tolerance: float = 0.0015
    # An algo order counts as belonging to a position when it triggered inside
    # [open_time - slack, close_time + slack].
    trigger_time_slack_ms: int = 60_000


@dataclass(frozen=True)
class Settings:
    credentials: Credentials
    base_url: str = "https://www.okx.com"
    bar: str = "1m"
    atr_period: int = 14
    cache_dir: Path = PROJECT_ROOT / "cache"
    output_dir: Path = PROJECT_ROOT / "output"
    extension: ExtensionWindowConfig = field(default_factory=ExtensionWindowConfig)
    match: MatchConfig = field(default_factory=MatchConfig)
    # How much history to pull before entry so ATR has a warm-up sample.
    pre_entry_pad_hours: float = 48.0
    # What-if multipliers explored by the optimizer.
    whatif_tp_mults: tuple[float, ...] = (0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0)
    whatif_sl_mults: tuple[float, ...] = (0.75, 1.0, 1.25, 1.5, 2.0)

    def ensure_dirs(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


def load_settings() -> Settings:
    creds = Credentials(
        api_key=_s("OKX_API_KEY", ""),
        api_secret=_s("OKX_API_SECRET", ""),
        passphrase=_s("OKX_API_PASSPHRASE", ""),
        simulated=_s("OKX_SIMULATED", "0") in ("1", "true", "True"),
    )
    return Settings(
        credentials=creds,
        base_url=_s("OKX_BASE_URL", "https://www.okx.com").rstrip("/"),
        bar=_s("CANDLE_BAR", "1m"),
        atr_period=_i("ATR_PERIOD", 14),
        cache_dir=Path(_s("CACHE_DIR", str(PROJECT_ROOT / "cache"))).expanduser(),
        output_dir=Path(_s("OUTPUT_DIR", str(PROJECT_ROOT / "output"))).expanduser(),
        extension=ExtensionWindowConfig(
            min_hours=_f("EXT_MIN_HOURS", 4.0),
            max_hours=_f("EXT_MAX_HOURS", 72.0),
            retrace_atr_mult=_f("EXT_RETRACE_ATR_MULT", 1.5),
            retrace_pct_fallback=_f("EXT_RETRACE_PCT_FALLBACK", 0.015),
            retrace_basis=_s("EXT_RETRACE_BASIS", "close"),
        ),
        match=MatchConfig(
            tick_tolerance=_f("CLOSE_MATCH_TICK_TOLERANCE", 8.0),
            pct_tolerance=_f("CLOSE_MATCH_PCT_TOLERANCE", 0.0015),
        ),
    )
