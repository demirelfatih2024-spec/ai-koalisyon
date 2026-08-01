"""MFE/MAE excursion analysis — the analytical core.

Conventions used throughout:

* For a **long**, the favourable extreme is a candle ``high`` and the adverse extreme is
  a candle ``low``. For a **short** the roles swap. ``Side.sign`` (+1/-1) converts a raw
  price delta into a signed P&L direction.
* **1R** is the entry-to-stop distance (``|entry - sl|``). Every ``*_r`` figure is in
  those units, so an MFE of +2.5R means price travelled two and a half times the risk
  in the favourable direction. When a trade has no recorded stop, R-figures are NaN
  rather than silently falling back to a made-up denominator.
* The **extension window** after a TP/SL trigger is adaptive: observe at least
  ``min_hours``, keep going while new favourable extremes keep printing, and stop once
  price gives back ``retrace_atr_mult * ATR`` from the running peak (or ``max_hours``
  elapses, or the data runs out). ATR adapts the threshold to each instrument's own
  volatility, which a flat percentage cannot do across BTC and a low-cap alt.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import pandas as pd

from config import ExtensionWindowConfig
from models import CloseReason, MatchedTrade, Side

HOUR_MS = 3_600_000
NAN = float("nan")


@dataclass
class Excursion:
    """Best/worst price reached over a span, with when it happened."""

    price: float = NAN
    ts: int = 0
    r: float = NAN
    pct: float = NAN


@dataclass
class ExtensionResult:
    """Outcome of watching price after the position already closed."""

    excursion: Excursion = field(default_factory=Excursion)
    adverse: Excursion = field(default_factory=Excursion)
    window_end_ts: int = 0
    stop_reason: str = "no_data"
    observed_hours: float = 0.0


@dataclass
class TradeAnalysis:
    trade: MatchedTrade
    atr: float = NAN
    # Entry -> close
    pre_close_mfe: Excursion = field(default_factory=Excursion)
    pre_close_mae: Excursion = field(default_factory=Excursion)
    mae_pct_of_sl_distance: float = NAN
    mfe_pct_of_tp_distance: float = NAN
    # After the close
    extension: ExtensionResult = field(default_factory=ExtensionResult)
    post_close_extra_r: float = NAN  # beyond the TP/SL price itself
    post_close_extra_pct: float = NAN
    # SL-specific reversal study
    would_have_reversed: bool | None = None
    time_to_reversal_ms: int | None = None
    reversal_drawdown_px: float = NAN
    reversal_drawdown_r: float = NAN
    notes: str = ""


# --------------------------------------------------------------------- helpers


def _signed_r(price: float, entry: float, side: Side, risk: float) -> float:
    if not math.isfinite(price) or not math.isfinite(risk) or risk <= 0:
        return NAN
    return (price - entry) * side.sign / risk


def _signed_pct(price: float, entry: float, side: Side) -> float:
    if not math.isfinite(price) or not math.isfinite(entry) or entry == 0:
        return NAN
    return (price - entry) * side.sign / abs(entry) * 100.0


def window(candles: pd.DataFrame, start_ts: int, end_ts: int) -> pd.DataFrame:
    if candles.empty:
        return candles
    mask = (candles["ts"] >= start_ts) & (candles["ts"] <= end_ts)
    return candles.loc[mask]


def favorable_excursion(
    candles: pd.DataFrame, side: Side, entry: float, risk: float
) -> Excursion:
    """Best price reached in the trade's direction."""
    if candles.empty:
        return Excursion()
    if side is Side.LONG:
        idx = candles["high"].idxmax()
        price = float(candles.loc[idx, "high"])
    else:
        idx = candles["low"].idxmin()
        price = float(candles.loc[idx, "low"])
    return Excursion(
        price=price,
        ts=int(candles.loc[idx, "ts"]),
        r=_signed_r(price, entry, side, risk),
        pct=_signed_pct(price, entry, side),
    )


def adverse_excursion(
    candles: pd.DataFrame, side: Side, entry: float, risk: float
) -> Excursion:
    """Worst price reached against the trade."""
    if candles.empty:
        return Excursion()
    if side is Side.LONG:
        idx = candles["low"].idxmin()
        price = float(candles.loc[idx, "low"])
    else:
        idx = candles["high"].idxmax()
        price = float(candles.loc[idx, "high"])
    return Excursion(
        price=price,
        ts=int(candles.loc[idx, "ts"]),
        r=_signed_r(price, entry, side, risk),
        pct=_signed_pct(price, entry, side),
    )


def track_extension(
    candles: pd.DataFrame,
    side: Side,
    start_ts: int,
    cfg: ExtensionWindowConfig,
    atr: float,
    reference_px: float,
    entry: float,
    risk: float,
) -> ExtensionResult:
    """Adaptive trailing-peak observation starting at ``start_ts``.

    Returns the furthest favourable point reached, the worst give-back along the way,
    and why observation stopped (``retrace`` / ``max_window`` / ``data_end``).
    """
    forward = candles[candles["ts"] >= start_ts]
    if forward.empty:
        return ExtensionResult()

    min_end = start_ts + int(cfg.min_hours * HOUR_MS)
    max_end = start_ts + int(cfg.max_hours * HOUR_MS)

    if math.isfinite(atr) and atr > 0:
        threshold = atr * cfg.retrace_atr_mult
    else:
        base = reference_px if math.isfinite(reference_px) else entry
        threshold = abs(base) * cfg.retrace_pct_fallback

    best_px = -math.inf if side is Side.LONG else math.inf
    best_ts = start_ts
    worst_px = math.inf if side is Side.LONG else -math.inf
    worst_ts = start_ts
    end_ts = start_ts
    stop_reason = "data_end"

    for ts, high, low, close in zip(
        forward["ts"].to_numpy(),
        forward["high"].to_numpy(),
        forward["low"].to_numpy(),
        forward["close"].to_numpy(),
    ):
        ts = int(ts)
        if ts > max_end:
            stop_reason = "max_window"
            break
        end_ts = ts

        if side is Side.LONG:
            if high > best_px:
                best_px, best_ts = float(high), ts
            if low < worst_px:
                worst_px, worst_ts = float(low), ts
            basis = float(close) if cfg.retrace_basis == "close" else float(low)
            giveback = best_px - basis
        else:
            if low < best_px:
                best_px, best_ts = float(low), ts
            if high > worst_px:
                worst_px, worst_ts = float(high), ts
            basis = float(close) if cfg.retrace_basis == "close" else float(high)
            giveback = basis - best_px

        if ts >= min_end and giveback >= threshold:
            stop_reason = "retrace"
            break

    if not math.isfinite(best_px):
        return ExtensionResult()

    return ExtensionResult(
        excursion=Excursion(
            price=best_px,
            ts=best_ts,
            r=_signed_r(best_px, entry, side, risk),
            pct=_signed_pct(best_px, entry, side),
        ),
        adverse=Excursion(
            price=worst_px,
            ts=worst_ts,
            r=_signed_r(worst_px, entry, side, risk),
            pct=_signed_pct(worst_px, entry, side),
        ),
        window_end_ts=end_ts,
        stop_reason=stop_reason,
        observed_hours=(end_ts - start_ts) / HOUR_MS,
    )


def _first_touch_ts(
    candles: pd.DataFrame, side: Side, target_px: float
) -> int | None:
    """First candle whose range reaches ``target_px`` in the favourable direction."""
    if candles.empty or not math.isfinite(target_px):
        return None
    if side is Side.LONG:
        hit = candles[candles["high"] >= target_px]
    else:
        hit = candles[candles["low"] <= target_px]
    if hit.empty:
        return None
    return int(hit.iloc[0]["ts"])


# ------------------------------------------------------------------- main API


def analyze_trade(
    trade: MatchedTrade,
    candles: pd.DataFrame,
    cfg: ExtensionWindowConfig,
    atr: float = NAN,
) -> TradeAnalysis:
    """Full excursion profile for one matched trade.

    ``candles`` must be ascending by ``ts`` and should span from (ideally before) the
    entry through the end of the maximum extension window.
    """
    pos = trade.position
    side = trade.side
    entry = trade.entry
    risk = trade.risk_per_unit
    result = TradeAnalysis(trade=trade, atr=atr)

    if candles.empty:
        result.notes = "no candle data available for this window"
        return result

    # ---- Entry -> close: what happened while the trade was live.
    live = window(candles, pos.open_time, pos.close_time)
    if live.empty:
        # Very short trades can close inside a single bar; widen by one bar each way.
        live = window(candles, pos.open_time - 60_000, pos.close_time + 60_000)

    result.pre_close_mfe = favorable_excursion(live, side, entry, risk)
    result.pre_close_mae = adverse_excursion(live, side, entry, risk)

    # How much of the stop distance did the trade actually consume?
    if math.isfinite(risk) and risk > 0 and math.isfinite(result.pre_close_mae.price):
        consumed = (entry - result.pre_close_mae.price) * side.sign
        result.mae_pct_of_sl_distance = max(consumed, 0.0) / risk * 100.0

    reward = trade.reward_per_unit
    if math.isfinite(reward) and reward > 0 and math.isfinite(result.pre_close_mfe.price):
        travelled = (result.pre_close_mfe.price - entry) * side.sign
        result.mfe_pct_of_tp_distance = max(travelled, 0.0) / reward * 100.0

    # ---- After the close: only meaningful for TP/SL exits.
    if trade.close_reason not in (CloseReason.TP_HIT, CloseReason.SL_HIT):
        result.notes = "post-close extension skipped (not a TP/SL exit)"
        return result

    close_ts = (
        trade.triggering_algo.trigger_time
        if trade.triggering_algo and trade.triggering_algo.trigger_time
        else pos.close_time
    )
    reference_px = pos.close_avg_px if math.isfinite(pos.close_avg_px) else entry

    result.extension = track_extension(
        candles=candles,
        side=side,
        start_ts=close_ts,
        cfg=cfg,
        atr=atr,
        reference_px=reference_px,
        entry=entry,
        risk=risk,
    )

    ext_px = result.extension.excursion.price
    if math.isfinite(ext_px) and math.isfinite(reference_px):
        extra = (ext_px - reference_px) * side.sign
        result.post_close_extra_pct = extra / abs(reference_px) * 100.0
        if math.isfinite(risk) and risk > 0:
            result.post_close_extra_r = extra / risk

    # ---- SL-specific: would the original TP have been reached anyway?
    if trade.close_reason is CloseReason.SL_HIT and math.isfinite(trade.tp_px):
        post = candles[
            (candles["ts"] >= close_ts)
            & (candles["ts"] <= close_ts + int(cfg.max_hours * HOUR_MS))
        ]
        touch_ts = _first_touch_ts(post, side, trade.tp_px)
        result.would_have_reversed = touch_ts is not None
        if touch_ts is not None:
            result.time_to_reversal_ms = touch_ts - close_ts
            # Worst further adverse move that would have had to be survived first.
            leg = post[post["ts"] <= touch_ts]
            drawdown = adverse_excursion(leg, side, entry, risk)
            result.reversal_drawdown_px = drawdown.price
            result.reversal_drawdown_r = drawdown.r

    return result
