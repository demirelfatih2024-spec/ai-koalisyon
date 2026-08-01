"""OHLCV retrieval with a local parquet cache.

Two things make this non-trivial and are handled explicitly here:

1. **Backward-only paging.** ``history-candles`` accepts ``after=ts`` (records older
   than ts) and ``before=ts``, but ``before`` returns the *newest* candles newer than
   ts rather than the ones immediately following it — verified against the live API.
   So every backfill walks backwards from the end of the range using ``after``.

2. **Coverage is tracked, not inferred.** A minute with no trades simply has no candle,
   so "row missing" cannot be used to mean "not yet downloaded". We persist an explicit
   list of covered ``[start, end]`` intervals per instrument alongside the parquet.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from okx_client import OKXClient

log = logging.getLogger(__name__)

BAR_MS = {
    "1m": 60_000,
    "3m": 180_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1H": 3_600_000,
    "2H": 7_200_000,
    "4H": 14_400_000,
    "1D": 86_400_000,
}

CANDLE_COLUMNS = ["ts", "open", "high", "low", "close", "vol"]

MAX_LIMIT = 300  # verified live: both candles and history-candles cap at 300


def merge_intervals(
    intervals: list[tuple[int, int]], tolerance_ms: int = 0
) -> list[tuple[int, int]]:
    """Union of intervals; adjacent ones within ``tolerance_ms`` are joined."""
    if not intervals:
        return []
    ordered = sorted(intervals)
    merged = [list(ordered[0])]
    for start, end in ordered[1:]:
        if start <= merged[-1][1] + tolerance_ms:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(a, b) for a, b in merged]


def subtract_intervals(
    need: tuple[int, int], covered: list[tuple[int, int]]
) -> list[tuple[int, int]]:
    """Portions of ``need`` not already inside ``covered``."""
    start, end = need
    gaps: list[tuple[int, int]] = []
    cursor = start
    for c_start, c_end in sorted(covered):
        if c_end < cursor:
            continue
        if c_start > end:
            break
        if c_start > cursor:
            gaps.append((cursor, min(c_start - 1, end)))
        cursor = max(cursor, c_end + 1)
        if cursor > end:
            break
    if cursor <= end:
        gaps.append((cursor, end))
    return [g for g in gaps if g[0] <= g[1]]


@dataclass
class _Store:
    frame: pd.DataFrame
    covered: list[tuple[int, int]]


class CandleFetcher:
    def __init__(self, client: OKXClient, cache_dir: Path, bar: str = "1m") -> None:
        if bar not in BAR_MS:
            raise ValueError(f"unsupported bar {bar!r}; known: {sorted(BAR_MS)}")
        self._client = client
        self._bar = bar
        self._dir = Path(cache_dir) / bar
        self._dir.mkdir(parents=True, exist_ok=True)
        self._mem: dict[str, _Store] = {}

    @property
    def bar_ms(self) -> int:
        return BAR_MS[self._bar]

    # ------------------------------------------------------------- cache I/O

    def _paths(self, inst_id: str) -> tuple[Path, Path]:
        safe = inst_id.replace("/", "_")
        return self._dir / f"{safe}.parquet", self._dir / f"{safe}.coverage.json"

    def _load(self, inst_id: str) -> _Store:
        if inst_id in self._mem:
            return self._mem[inst_id]
        pq, cov = self._paths(inst_id)
        if pq.exists():
            frame = pd.read_parquet(pq)
        else:
            frame = pd.DataFrame(columns=CANDLE_COLUMNS).astype(
                {"ts": "int64", **{c: "float64" for c in CANDLE_COLUMNS[1:]}}
            )
        covered = json.loads(cov.read_text()) if cov.exists() else []
        store = _Store(frame=frame, covered=[tuple(x) for x in covered])
        self._mem[inst_id] = store
        return store

    def _persist(self, inst_id: str) -> None:
        store = self._mem[inst_id]
        pq, cov = self._paths(inst_id)
        store.frame.to_parquet(pq, index=False)
        cov.write_text(json.dumps([list(x) for x in store.covered]))

    # -------------------------------------------------------------- fetching

    def _download_range(self, inst_id: str, start_ms: int, end_ms: int) -> pd.DataFrame:
        """Walk backwards from ``end_ms`` to ``start_ms``, newest page first."""
        rows: list[list[str]] = []
        cursor = end_ms + self.bar_ms  # ensure the candle at end_ms is included
        pages = 0
        while True:
            page = self._client.get_history_candles(
                inst_id, self._bar, after_ms=cursor, limit=MAX_LIMIT
            )
            pages += 1
            if not page:
                break
            rows.extend(page)
            oldest = min(int(r[0]) for r in page)
            if oldest <= start_ms or len(page) < MAX_LIMIT:
                break
            cursor = oldest
            if pages > 5000:  # safety valve against a pathological loop
                log.warning("aborting %s backfill after %d pages", inst_id, pages)
                break

        if not rows:
            return pd.DataFrame(columns=CANDLE_COLUMNS)

        frame = pd.DataFrame(
            [
                {
                    "ts": int(r[0]),
                    "open": float(r[1]),
                    "high": float(r[2]),
                    "low": float(r[3]),
                    "close": float(r[4]),
                    "vol": float(r[5]) if len(r) > 5 and r[5] else 0.0,
                    "confirm": int(r[8]) if len(r) > 8 and r[8] != "" else 1,
                }
                for r in rows
            ]
        )
        # Drop the still-forming candle: its high/low are not final.
        frame = frame[frame["confirm"] == 1].drop(columns=["confirm"])
        return frame[CANDLE_COLUMNS]

    def ensure(self, inst_id: str, ranges: list[tuple[int, int]]) -> None:
        """Guarantee every requested range is present in the cache."""
        if not ranges:
            return
        store = self._load(inst_id)
        wanted = merge_intervals(ranges, tolerance_ms=self.bar_ms * 60)

        missing: list[tuple[int, int]] = []
        for rng in wanted:
            missing.extend(subtract_intervals(rng, store.covered))
        missing = merge_intervals(missing, tolerance_ms=self.bar_ms * 60)
        if not missing:
            return

        new_frames = [store.frame]
        for start, end in missing:
            log.info(
                "fetching %s %s %s..%s",
                inst_id,
                self._bar,
                pd.to_datetime(start, unit="ms", utc=True),
                pd.to_datetime(end, unit="ms", utc=True),
            )
            got = self._download_range(inst_id, start, end)
            if not got.empty:
                new_frames.append(got)

        combined = pd.concat(new_frames, ignore_index=True)
        combined = (
            combined.drop_duplicates(subset="ts", keep="last")
            .sort_values("ts")
            .reset_index(drop=True)
        )
        store.frame = combined
        # Record coverage even where OKX returned nothing, so we do not re-request
        # ranges that are genuinely empty (delisted or pre-listing instruments).
        store.covered = merge_intervals(store.covered + missing, tolerance_ms=self.bar_ms)
        self._persist(inst_id)

    # --------------------------------------------------------------- reading

    def get(self, inst_id: str, start_ms: int, end_ms: int) -> pd.DataFrame:
        """Cached candles within [start_ms, end_ms], ascending by ts."""
        store = self._load(inst_id)
        if store.frame.empty:
            return store.frame.copy()
        f = store.frame
        return f[(f["ts"] >= start_ms) & (f["ts"] <= end_ms)].reset_index(drop=True)


def resample_ohlc(frame: pd.DataFrame, rule: str = "1h") -> pd.DataFrame:
    """Aggregate fine-grained candles up to a coarser bar (used for ATR)."""
    if frame.empty:
        return frame.copy()
    idx = pd.to_datetime(frame["ts"], unit="ms", utc=True)
    out = (
        frame.set_index(idx)
        .resample(rule)
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "vol": "sum"})
        .dropna(subset=["open", "high", "low", "close"])
    )
    out = out.reset_index(names="dt")
    # Normalise to millisecond resolution before the integer cast. pandas picks the
    # datetime unit from the input (ms here, ns historically), so casting straight to
    # int64 without pinning the resolution silently changes the scale.
    stamps = out["dt"]
    if getattr(stamps.dtype, "tz", None) is not None:
        stamps = stamps.dt.tz_convert("UTC").dt.tz_localize(None)
    out["ts"] = stamps.astype("datetime64[ms]").astype("int64")
    return out[CANDLE_COLUMNS]


def average_true_range(frame: pd.DataFrame, period: int = 14) -> float:
    """Wilder ATR over the final ``period`` bars. NaN-safe; 0.0 when unavailable."""
    if frame.empty or len(frame) < 2:
        return 0.0
    high = frame["high"].astype(float)
    low = frame["low"].astype(float)
    prev_close = frame["close"].astype(float).shift(1)
    true_range = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    tail = true_range.dropna().tail(period)
    if tail.empty:
        return 0.0
    return float(tail.mean())
