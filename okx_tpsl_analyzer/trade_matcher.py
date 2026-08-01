"""Join closed positions to the TP/SL algo orders that governed them, then classify
how each position actually ended.

Classification precedence — strongest evidence first:

1. ``positions-history.type`` 3/4 -> liquidation, 5/6 -> ADL. These are stated by the
   exchange and outrank everything else.
2. ``orders-algo-history.actualSide`` (``tp``/``sl``) on an *effective* algo order whose
   ``triggerTime`` falls inside the position's lifetime. OKX tells us outright which leg
   fired, so this beats reverse-engineering it from the close price.
3. Price proximity: ``closeAvgPx`` within tolerance of a known TP or SL trigger price.
   Used when no algo record survives (e.g. the order predates the 3-month retention).
4. Otherwise MANUAL.
"""
from __future__ import annotations

import logging
from collections import defaultdict

from config import MatchConfig
from models import AlgoOrder, CloseReason, ClosedPosition, Instrument, MatchedTrade, Side

log = logging.getLogger(__name__)


def _tolerance(price: float, instrument: Instrument | None, cfg: MatchConfig) -> float:
    """Absolute price tolerance: the looser of N ticks and a percentage of price."""
    pct = abs(price) * cfg.pct_tolerance
    ticks = (instrument.tick_sz * cfg.tick_tolerance) if instrument else 0.0
    return max(pct, ticks)


def _overlaps(order: AlgoOrder, pos: ClosedPosition, slack: int) -> bool:
    """Was this algo order alive at any point during the position's life?"""
    created = order.c_time or order.u_time
    ended = order.trigger_time or order.u_time or order.c_time
    if not created:
        return False
    # Created before the position closed, and not already finished before it opened.
    return created <= pos.close_time + slack and ended >= pos.open_time - slack


def _levels_from(orders: list[AlgoOrder]) -> tuple[float, float]:
    """Governing TP and SL prices: the most recently created order that defines each."""
    tp = sl = float("nan")
    for order in sorted(orders, key=lambda o: o.c_time):
        if order.tp_trigger_px == order.tp_trigger_px:  # not NaN
            tp = order.tp_trigger_px
        if order.sl_trigger_px == order.sl_trigger_px:
            sl = order.sl_trigger_px
    return tp, sl


def match_trades(
    positions: list[ClosedPosition],
    algo_orders: list[AlgoOrder],
    instruments: dict[str, Instrument],
    cfg: MatchConfig,
) -> list[MatchedTrade]:
    by_inst: dict[str, list[AlgoOrder]] = defaultdict(list)
    for order in algo_orders:
        by_inst[order.inst_id].append(order)

    trades: list[MatchedTrade] = []
    for pos in positions:
        instrument = instruments.get(pos.inst_id)
        candidates = [
            o for o in by_inst.get(pos.inst_id, []) if _overlaps(o, pos, cfg.trigger_time_slack_ms)
        ]
        tp_px, sl_px = _levels_from(candidates)

        trade = MatchedTrade(
            position=pos,
            instrument=instrument,
            tp_px=tp_px,
            sl_px=sl_px,
            algo_orders=candidates,
        )
        _classify(trade, cfg)
        trades.append(trade)

    return trades


def _classify(trade: MatchedTrade, cfg: MatchConfig) -> None:
    pos = trade.position

    # (1) Exchange-stated forced closes.
    if pos.close_type in (3, 4):
        trade.close_reason = CloseReason.LIQUIDATION
        trade.classification_basis = f"positions-history.type={pos.close_type}"
        return
    if pos.close_type in (5, 6):
        trade.close_reason = CloseReason.ADL
        trade.classification_basis = f"positions-history.type={pos.close_type}"
        return

    # (2) actualSide on an algo order that fired during the position's life.
    slack = cfg.trigger_time_slack_ms
    fired = [
        o
        for o in trade.algo_orders
        if o.triggered
        and o.actual_side in ("tp", "sl")
        and pos.open_time - slack <= o.trigger_time <= pos.close_time + slack
    ]
    if fired:
        # If several fired (scaled exits), the one closest to the close wins.
        best = min(fired, key=lambda o: abs(o.trigger_time - pos.close_time))
        trade.triggering_algo = best
        trade.close_reason = (
            CloseReason.TP_HIT if best.actual_side == "tp" else CloseReason.SL_HIT
        )
        trade.classification_basis = f"algo.actualSide={best.actual_side} (algoId={best.algo_id})"
        # Prefer the levels carried by the order that actually fired.
        if best.tp_trigger_px == best.tp_trigger_px:
            trade.tp_px = best.tp_trigger_px
        if best.sl_trigger_px == best.sl_trigger_px:
            trade.sl_px = best.sl_trigger_px
        return

    # (3) Fall back to price proximity against the known levels.
    close_px = pos.close_avg_px
    if close_px == close_px:
        tp_hit = trade.tp_px == trade.tp_px and abs(close_px - trade.tp_px) <= _tolerance(
            trade.tp_px, trade.instrument, cfg
        )
        sl_hit = trade.sl_px == trade.sl_px and abs(close_px - trade.sl_px) <= _tolerance(
            trade.sl_px, trade.instrument, cfg
        )
        # If both match, the side the price actually favours decides.
        if tp_hit and sl_hit:
            gain = (close_px - trade.entry) * trade.side.sign
            tp_hit, sl_hit = gain >= 0, gain < 0
        if tp_hit:
            trade.close_reason = CloseReason.TP_HIT
            trade.classification_basis = "closeAvgPx within tolerance of tpTriggerPx"
            return
        if sl_hit:
            trade.close_reason = CloseReason.SL_HIT
            trade.classification_basis = "closeAvgPx within tolerance of slTriggerPx"
            return

    trade.close_reason = CloseReason.MANUAL
    trade.classification_basis = (
        "no algo trigger and close price matches neither level"
        if trade.algo_orders
        else "no TP/SL algo order found for this position"
    )


def summarize_matching(trades: list[MatchedTrade]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for t in trades:
        counts[t.close_reason.value] += 1
    counts["WITH_TP_LEVEL"] = sum(1 for t in trades if t.tp_px == t.tp_px)
    counts["WITH_SL_LEVEL"] = sum(1 for t in trades if t.sl_px == t.sl_px)
    counts["TOTAL"] = len(trades)
    return dict(counts)
