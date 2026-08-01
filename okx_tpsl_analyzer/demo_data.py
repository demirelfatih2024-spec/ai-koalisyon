"""Synthetic positions, algo orders and candles.

Lets the whole pipeline be exercised (and the report inspected) before any API key
exists. Deliberately mixes TP hits, SL hits that later reverse, SL hits that keep
falling, a liquidation and a manual close so every branch gets touched.
"""
from __future__ import annotations

import random

import numpy as np
import pandas as pd

MIN_MS = 60_000
HOUR_MS = 3_600_000


def _walk(start_px: float, n: int, drift: float, vol: float, rng: random.Random) -> list[float]:
    px = start_px
    out = []
    for _ in range(n):
        px *= 1 + drift + rng.gauss(0, vol)
        out.append(px)
    return out


def _to_candles(prices: list[float], start_ts: int, vol: float, rng: random.Random) -> pd.DataFrame:
    rows = []
    prev = prices[0]
    for i, px in enumerate(prices):
        spread = abs(px) * vol * 0.6
        rows.append(
            {
                "ts": start_ts + i * MIN_MS,
                "open": prev,
                "high": max(prev, px) + abs(rng.gauss(0, spread)),
                "low": min(prev, px) - abs(rng.gauss(0, spread)),
                "close": px,
                "vol": 100.0,
            }
        )
        prev = px
    return pd.DataFrame(rows)


def build_demo(seed: int = 7, n_trades: int = 40, base_ts: int = 1_780_000_000_000):
    """Return (positions_raw, algo_raw, instruments_raw, candles_by_inst)."""
    rng = random.Random(seed)
    symbols = [
        ("BTC-USDT-SWAP", 65000.0, 0.0006, 0.1),
        ("ETH-USDT-SWAP", 3200.0, 0.0009, 0.01),
        ("SOL-USDT-SWAP", 150.0, 0.0014, 0.01),
    ]

    positions: list[dict] = []
    algos: list[dict] = []
    candles: dict[str, list[pd.DataFrame]] = {s[0]: [] for s in symbols}

    cursor = base_ts
    for i in range(n_trades):
        inst_id, base_px, vol, tick = symbols[i % len(symbols)]
        side = "long" if rng.random() < 0.55 else "short"
        sign = 1 if side == "long" else -1
        entry = base_px * (1 + rng.gauss(0, 0.02))

        risk_pct = rng.uniform(0.006, 0.02)
        rr = rng.uniform(1.2, 3.0)
        sl_px = entry - sign * entry * risk_pct
        tp_px = entry + sign * entry * risk_pct * rr

        open_ts = cursor
        # Build a path: to the exit, then a long tail for the extension window.
        pre_len = rng.randint(60, 400)
        tail_len = 6 * 60 + rng.randint(0, 3000)

        roll = rng.random()
        if roll < 0.42:
            outcome = "tp"
        elif roll < 0.85:
            outcome = "sl"
        elif roll < 0.93:
            outcome = "manual"
        else:
            outcome = "liq"

        target = tp_px if outcome == "tp" else sl_px if outcome in ("sl", "liq") else entry * (1 + sign * risk_pct * 0.4)
        # Linear drift toward the exit level, with noise.
        pre = list(np.linspace(entry, target, pre_len) * (1 + np.random.normal(0, vol * 0.3, pre_len)))
        close_ts = open_ts + (pre_len - 1) * MIN_MS
        close_px = target

        # Tail behaviour after the exit.
        if outcome == "tp":
            drift = sign * (vol * rng.uniform(0.05, 0.5)) if rng.random() < 0.7 else -sign * vol * 0.2
        elif outcome == "sl":
            drift = sign * (vol * rng.uniform(0.1, 0.6)) if rng.random() < 0.45 else -sign * vol * 0.3
        else:
            drift = rng.choice([1, -1]) * vol * 0.2
        tail = _walk(target, tail_len, drift * 0.02, vol * 0.35, rng)

        frame = _to_candles(pre + tail, open_ts, vol, rng)
        candles[inst_id].append(frame)

        close_type = 3 if outcome == "liq" else 2
        positions.append(
            {
                "posId": f"demo-{i}",
                "instId": inst_id,
                "instType": "SWAP",
                "mgnMode": "cross",
                "direction": side,
                "posSide": "net",
                "lever": "10",
                "openAvgPx": f"{entry:.6f}",
                "closeAvgPx": f"{close_px:.6f}",
                "openMaxPos": "10",
                "closeTotalPos": "10",
                "realizedPnl": f"{(close_px - entry) * sign:.4f}",
                "pnl": f"{(close_px - entry) * sign:.4f}",
                "pnlRatio": "0.01",
                "fee": "-0.5",
                "fundingFee": "0",
                "liqPenalty": "0",
                "cTime": str(open_ts),
                "uTime": str(close_ts),
                "type": str(close_type),
            }
        )

        actual_side = "tp" if outcome == "tp" else "sl" if outcome == "sl" else ""
        algos.append(
            {
                "algoId": str(900_000_000 + i),
                "instId": inst_id,
                "instType": "SWAP",
                "posSide": "net",
                "side": "sell" if side == "long" else "buy",
                "ordType": "oco",
                "state": "effective" if actual_side else "canceled",
                "tpTriggerPx": f"{tp_px:.6f}",
                "tpOrdPx": "-1",
                "tpTriggerPxType": "last",
                "slTriggerPx": f"{sl_px:.6f}",
                "slOrdPx": "-1",
                "slTriggerPxType": "mark",
                "actualSide": actual_side,
                "actualSz": "10",
                "sz": "10",
                "cTime": str(open_ts),
                "uTime": str(close_ts),
                "triggerTime": str(close_ts) if actual_side else "0",
            }
        )
        cursor = close_ts + (tail_len + 120) * MIN_MS

    instruments = [
        {
            "instId": s[0],
            "instType": "SWAP",
            "ctType": "linear",
            "ctVal": "0.01",
            "ctMult": "1",
            "tickSz": str(s[3]),
            "settleCcy": "USDT",
        }
        for s in symbols
    ]

    merged = {
        inst: pd.concat(frames, ignore_index=True)
        .drop_duplicates(subset="ts")
        .sort_values("ts")
        .reset_index(drop=True)
        for inst, frames in candles.items()
        if frames
    }
    return positions, algos, instruments, merged
