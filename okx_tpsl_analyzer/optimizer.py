"""Turn the excursion record into TP/SL recommendations.

Three complementary views:

1. **Distributions** — where MFE and MAE actually landed, in R, with percentiles.
2. **TP sweep** — an analytic pass over candidate TP distances. For a target of X R,
   the historical hit rate is the share of trades whose MFE reached X, and expectancy
   follows directly. This answers "which TP distance maximises expectancy" without
   re-walking price.
3. **What-if backtest** — re-simulates each trade bar by bar against alternative TP/SL
   multipliers, so ordering effects (which level is touched first) are respected.

**Intrabar ambiguity.** When one candle's range spans both the alternative TP and the
alternative SL, 1-minute OHLC cannot say which came first. We resolve those bars
*against* the trade (stop assumed first). That biases results pessimistically, which is
the correct direction for a sizing decision — but it means a scenario's edge is a floor,
not a point estimate. ``ambiguous_bars`` reports how often it happened.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from excursion_analyzer import HOUR_MS, TradeAnalysis
from models import CloseReason, Side

log = logging.getLogger(__name__)
NAN = float("nan")

# Above this share of unresolved trades, a scenario's headline expectancy is driven by
# marking open trades to the end of the data rather than by the TP/SL rule itself.
MAX_TIMEOUT_SHARE = 0.35


@dataclass
class ScenarioResult:
    tp_mult: float
    sl_mult: float
    trades: int = 0
    wins: int = 0
    losses: int = 0
    timeouts: int = 0
    total_r: float = 0.0
    timeout_r: float = 0.0
    expectancy_r: float = NAN
    resolved_expectancy_r: float = NAN
    win_rate: float = NAN
    profit_factor: float = NAN
    max_drawdown_r: float = NAN
    ambiguous_bars: int = 0
    equity_curve: list[float] = field(default_factory=list)

    @property
    def timeout_share(self) -> float:
        return self.timeouts / self.trades if self.trades else NAN

    @property
    def is_reliable(self) -> bool:
        """Enough trades actually resolved for the result to mean anything."""
        return math.isfinite(self.timeout_share) and self.timeout_share <= MAX_TIMEOUT_SHARE

    def as_row(self) -> dict[str, float | int | str]:
        def r(value: float, digits: int = 4) -> float:
            return round(value, digits) if isinstance(value, float) and math.isfinite(value) else NAN

        return {
            "tp_mult": self.tp_mult,
            "sl_mult": self.sl_mult,
            "trades": self.trades,
            "wins": self.wins,
            "losses": self.losses,
            "timeouts": self.timeouts,
            "timeout_%": r(self.timeout_share * 100, 1),
            "win_rate_%": r(self.win_rate * 100, 2),
            "expectancy_R": r(self.expectancy_r),
            "resolved_expectancy_R": r(self.resolved_expectancy_r),
            "total_R": r(self.total_r, 3),
            "R_from_timeouts": r(self.timeout_r, 3),
            "profit_factor": r(self.profit_factor, 3),
            "max_drawdown_R": r(self.max_drawdown_r, 3),
            "ambiguous_bars": self.ambiguous_bars,
            "reliable": self.is_reliable,
        }


# ------------------------------------------------------------------ utilities


def trade_key(analysis: TradeAnalysis) -> str:
    pos = analysis.trade.position
    return f"{pos.pos_id}:{pos.close_time}"


def _max_drawdown(equity: list[float]) -> float:
    if not equity:
        return NAN
    peak = equity[0]
    worst = 0.0
    for value in equity:
        peak = max(peak, value)
        worst = min(worst, value - peak)
    return abs(worst)


def overall_mfe_r(analysis: TradeAnalysis) -> float:
    """Best favourable excursion in R across the live trade *and* its extension."""
    candidates = [analysis.pre_close_mfe.r, analysis.extension.excursion.r]
    finite = [c for c in candidates if isinstance(c, float) and math.isfinite(c)]
    return max(finite) if finite else NAN


# ------------------------------------------------------------- distributions


def excursion_frame(analyses: list[TradeAnalysis]) -> pd.DataFrame:
    rows = []
    for a in analyses:
        pos = a.trade.position
        rows.append(
            {
                "instId": pos.inst_id,
                "posSide": a.trade.side.value,
                "closeReason": a.trade.close_reason.value,
                "entry": a.trade.entry,
                "tpPx": a.trade.tp_px,
                "slPx": a.trade.sl_px,
                "risk_per_unit": a.trade.risk_per_unit,
                "reward_per_unit": a.trade.reward_per_unit,
                "planned_rr": (
                    a.trade.reward_per_unit / a.trade.risk_per_unit
                    if math.isfinite(a.trade.risk_per_unit)
                    and a.trade.risk_per_unit > 0
                    and math.isfinite(a.trade.reward_per_unit)
                    else NAN
                ),
                "preClose_MFE_R": a.pre_close_mfe.r,
                "preClose_MAE_R": a.pre_close_mae.r,
                "MAE_%ofSLdistance": a.mae_pct_of_sl_distance,
                "MFE_%ofTPdistance": a.mfe_pct_of_tp_distance,
                "postClose_MFE_R": a.extension.excursion.r,
                "postClose_extra_R": a.post_close_extra_r,
                "overall_MFE_R": overall_mfe_r(a),
                "wouldHaveReversed": a.would_have_reversed,
                "reversal_drawdown_R": a.reversal_drawdown_r,
            }
        )
    return pd.DataFrame(rows)


def describe_distributions(
    frame: pd.DataFrame, percentiles: tuple[float, ...] = (10, 25, 50, 75, 90, 95)
) -> pd.DataFrame:
    cols = [
        "preClose_MFE_R",
        "preClose_MAE_R",
        "MAE_%ofSLdistance",
        "postClose_extra_R",
        "overall_MFE_R",
    ]
    out = {}
    for col in cols:
        if col not in frame:
            continue
        series = pd.to_numeric(frame[col], errors="coerce").dropna()
        if series.empty:
            continue
        stats = {"count": len(series), "mean": series.mean(), "std": series.std()}
        for p in percentiles:
            stats[f"p{int(p)}"] = series.quantile(p / 100.0)
        out[col] = stats
    return pd.DataFrame(out).T


# ------------------------------------------------------------------ TP sweep


def tp_sweep(
    analyses: list[TradeAnalysis],
    targets_r: np.ndarray | None = None,
    loss_r: float = -1.0,
) -> pd.DataFrame:
    """Historical hit rate and expectancy for each candidate TP distance.

    A trade "would have hit" a TP of X R if its overall MFE reached X R. Trades that
    did not are charged ``loss_r`` (a full stop by default). This ignores ordering
    within a bar and so is an upper bound — the bar-by-bar backtest below is stricter.
    """
    if targets_r is None:
        targets_r = np.arange(0.25, 8.01, 0.25)

    mfes = np.array(
        [overall_mfe_r(a) for a in analyses if math.isfinite(overall_mfe_r(a))]
    )
    if mfes.size == 0:
        return pd.DataFrame()

    rows = []
    for target in targets_r:
        hits = int((mfes >= target).sum())
        n = mfes.size
        hit_rate = hits / n
        expectancy = hit_rate * target + (1 - hit_rate) * loss_r
        rows.append(
            {
                "tp_target_R": round(float(target), 3),
                "hit_rate_%": round(hit_rate * 100, 2),
                "n_trades": n,
                "expectancy_R": round(expectancy, 4),
            }
        )
    return pd.DataFrame(rows)


# ------------------------------------------------------------ what-if engine


def _simulate_one(
    analysis: TradeAnalysis,
    candles: pd.DataFrame,
    tp_mult: float,
    sl_mult: float,
    max_hours: float,
) -> tuple[str, float, int] | None:
    """Replay a single trade against scaled TP/SL levels.

    Returns ``(outcome, r_result, ambiguous_bars)`` or None when the trade cannot be
    simulated (missing baseline TP/SL, or no candles).
    """
    trade = analysis.trade
    pos = trade.position
    entry, side = trade.entry, trade.side
    risk, reward = trade.risk_per_unit, trade.reward_per_unit

    if not (math.isfinite(risk) and risk > 0 and math.isfinite(reward) and reward > 0):
        return None
    if candles.empty:
        return None

    tp_dist = reward * tp_mult
    sl_dist = risk * sl_mult
    tp_px = entry + side.sign * tp_dist
    sl_px = entry - side.sign * sl_dist

    horizon_end = pos.close_time + int(max_hours * HOUR_MS)
    path = candles[(candles["ts"] >= pos.open_time) & (candles["ts"] <= horizon_end)]
    if path.empty:
        return None

    ambiguous = 0
    for high, low in zip(path["high"].to_numpy(), path["low"].to_numpy()):
        if side is Side.LONG:
            tp_touched, sl_touched = high >= tp_px, low <= sl_px
        else:
            tp_touched, sl_touched = low <= tp_px, high >= sl_px

        if tp_touched and sl_touched:
            ambiguous += 1
            return ("loss", -sl_mult, ambiguous)  # conservative: stop assumed first
        if tp_touched:
            return ("win", tp_dist / risk, ambiguous)
        if sl_touched:
            return ("loss", -sl_mult, ambiguous)

    # Neither level reached inside the horizon — mark to the final close.
    final = float(path["close"].iloc[-1])
    return ("timeout", (final - entry) * side.sign / risk, ambiguous)


def whatif_backtest(
    analyses: list[TradeAnalysis],
    candles_by_trade: dict[str, pd.DataFrame],
    tp_mults: tuple[float, ...],
    sl_mults: tuple[float, ...],
    max_hours: float = 72.0,
    only_reasons: tuple[CloseReason, ...] = (CloseReason.TP_HIT, CloseReason.SL_HIT),
) -> tuple[pd.DataFrame, list[ScenarioResult]]:
    """Grid-search TP/SL multipliers over the historical trade set."""
    eligible = [a for a in analyses if a.trade.close_reason in only_reasons]
    if not eligible:
        log.warning("no TP/SL-closed trades available for the what-if backtest")
        return pd.DataFrame(), []

    results: list[ScenarioResult] = []
    for tp_mult in tp_mults:
        for sl_mult in sl_mults:
            scenario = ScenarioResult(tp_mult=tp_mult, sl_mult=sl_mult)
            running = 0.0
            for analysis in eligible:
                candles = candles_by_trade.get(trade_key(analysis))
                if candles is None:
                    continue
                outcome = _simulate_one(analysis, candles, tp_mult, sl_mult, max_hours)
                if outcome is None:
                    continue
                kind, r_value, ambiguous = outcome
                scenario.trades += 1
                scenario.ambiguous_bars += ambiguous
                scenario.total_r += r_value
                running += r_value
                scenario.equity_curve.append(running)
                if kind == "win":
                    scenario.wins += 1
                elif kind == "loss":
                    scenario.losses += 1
                else:
                    scenario.timeouts += 1
                    scenario.timeout_r += r_value

            if scenario.trades:
                decided = scenario.wins + scenario.losses
                scenario.win_rate = scenario.wins / decided if decided else NAN
                scenario.expectancy_r = scenario.total_r / scenario.trades
                # Expectancy over only the trades that actually reached a level. This
                # strips out the mark-to-market on unresolved trades, which otherwise
                # dominates any scenario with a distant TP.
                scenario.resolved_expectancy_r = (
                    (scenario.total_r - scenario.timeout_r) / decided if decided else NAN
                )
                gains = sum(x for x in _diffs(scenario.equity_curve) if x > 0)
                pains = abs(sum(x for x in _diffs(scenario.equity_curve) if x < 0))
                scenario.profit_factor = gains / pains if pains > 0 else math.inf
                scenario.max_drawdown_r = _max_drawdown(scenario.equity_curve)
            results.append(scenario)

    frame = pd.DataFrame([r.as_row() for r in results])
    if not frame.empty:
        # Reliable scenarios first, then by expectancy — so a grid position that only
        # looks good because most of its trades never resolved cannot top the table.
        frame = frame.sort_values(
            ["reliable", "expectancy_R"], ascending=[False, False]
        ).reset_index(drop=True)
    return frame, results


def best_scenario(scenarios: pd.DataFrame) -> pd.Series | None:
    """Highest-expectancy scenario that is not dominated by unresolved trades."""
    if scenarios.empty:
        return None
    reliable = scenarios[scenarios["reliable"]]
    pool = reliable if not reliable.empty else scenarios
    return pool.loc[pool["expectancy_R"].idxmax()]


def _diffs(curve: list[float]) -> list[float]:
    out = []
    prev = 0.0
    for value in curve:
        out.append(value - prev)
        prev = value
    return out


# --------------------------------------------------- scaled / partial exits


def scaled_exit_study(
    analyses: list[TradeAnalysis],
    candles_by_trade: dict[str, pd.DataFrame],
    first_fraction: float = 0.5,
    runner_tp_mults: tuple[float, ...] = (1.5, 2.0, 3.0),
    move_stop_to_breakeven: bool = True,
    max_hours: float = 72.0,
) -> pd.DataFrame:
    """"What if I had used a second target?" — currently unused, so this is exploratory.

    Models taking ``first_fraction`` of the position off at the original TP and letting
    the remainder run to a further target, optionally with the stop moved to breakeven
    once the first target fills.
    """
    eligible = [
        a
        for a in analyses
        if a.trade.close_reason in (CloseReason.TP_HIT, CloseReason.SL_HIT)
    ]
    rows = []
    for runner_mult in runner_tp_mults:
        total_r = 0.0
        counted = 0
        runner_hits = 0
        runner_stopped = 0
        for analysis in eligible:
            trade = analysis.trade
            risk, reward = trade.risk_per_unit, trade.reward_per_unit
            candles = candles_by_trade.get(trade_key(analysis))
            if candles is None or candles.empty:
                continue
            if not (math.isfinite(risk) and risk > 0 and math.isfinite(reward) and reward > 0):
                continue

            entry, side = trade.entry, trade.side
            pos = trade.position
            tp1 = entry + side.sign * reward
            sl0 = entry - side.sign * risk
            tp2 = entry + side.sign * reward * runner_mult

            horizon_end = pos.close_time + int(max_hours * HOUR_MS)
            path = candles[
                (candles["ts"] >= pos.open_time) & (candles["ts"] <= horizon_end)
            ]
            if path.empty:
                continue

            counted += 1
            first_filled = False
            stop_px = sl0
            realized = 0.0
            resolved = False

            for high, low, close in zip(
                path["high"].to_numpy(), path["low"].to_numpy(), path["close"].to_numpy()
            ):
                if side is Side.LONG:
                    hit_stop, hit_tp1, hit_tp2 = low <= stop_px, high >= tp1, high >= tp2
                else:
                    hit_stop, hit_tp1, hit_tp2 = high >= stop_px, low <= tp1, low <= tp2

                if not first_filled:
                    if hit_stop:  # conservative when a bar spans both
                        realized = -1.0
                        resolved = True
                        break
                    if hit_tp1:
                        first_filled = True
                        realized += first_fraction * (reward / risk)
                        if move_stop_to_breakeven:
                            stop_px = entry
                        if hit_tp2:  # same bar carried straight through
                            realized += (1 - first_fraction) * (reward * runner_mult / risk)
                            runner_hits += 1
                            resolved = True
                            break
                    continue

                if hit_stop:
                    remainder_r = 0.0 if move_stop_to_breakeven else -1.0
                    realized += (1 - first_fraction) * remainder_r
                    runner_stopped += 1
                    resolved = True
                    break
                if hit_tp2:
                    realized += (1 - first_fraction) * (reward * runner_mult / risk)
                    runner_hits += 1
                    resolved = True
                    break

            if not resolved:
                final = float(path["close"].iloc[-1])
                remainder_r = (final - entry) * side.sign / risk
                if first_filled:
                    realized += (1 - first_fraction) * remainder_r
                else:
                    realized = remainder_r
            total_r += realized

        rows.append(
            {
                "first_fraction": first_fraction,
                "runner_tp_mult": runner_mult,
                "stop_to_breakeven": move_stop_to_breakeven,
                "trades": counted,
                "runner_target_hits": runner_hits,
                "runner_stopped_out": runner_stopped,
                "total_R": round(total_r, 3),
                "expectancy_R": round(total_r / counted, 4) if counted else NAN,
            }
        )
    return pd.DataFrame(rows)


# ------------------------------------------------------------ recommendations


def recommend_levels(
    frame: pd.DataFrame, min_trades: int = 8
) -> pd.DataFrame:
    """Per-symbol TP/SL guidance drawn from the realised excursion distribution."""
    if frame.empty:
        return pd.DataFrame()

    rows = []
    for inst_id, group in frame.groupby("instId"):
        mfe = pd.to_numeric(group["overall_MFE_R"], errors="coerce").dropna()
        mae = pd.to_numeric(group["MAE_%ofSLdistance"], errors="coerce").dropna()
        planned = pd.to_numeric(group["planned_rr"], errors="coerce").dropna()
        if len(group) < min_trades:
            note = f"only {len(group)} trades — treat as indicative, not significant"
        else:
            note = ""
        rows.append(
            {
                "instId": inst_id,
                "trades": len(group),
                "median_planned_RR": round(planned.median(), 2) if not planned.empty else NAN,
                "median_MFE_R": round(mfe.median(), 2) if not mfe.empty else NAN,
                "p75_MFE_R": round(mfe.quantile(0.75), 2) if not mfe.empty else NAN,
                "p90_MFE_R": round(mfe.quantile(0.90), 2) if not mfe.empty else NAN,
                # A stop only needs to clear the worst adverse move it actually saw.
                "p90_MAE_%ofSL": round(mae.quantile(0.90), 1) if not mae.empty else NAN,
                "median_MAE_%ofSL": round(mae.median(), 1) if not mae.empty else NAN,
                "suggested_SL_scale": (
                    round(max(mae.quantile(0.90) / 100.0, 0.3), 2) if not mae.empty else NAN
                ),
                "note": note,
            }
        )
    return pd.DataFrame(rows).sort_values("trades", ascending=False).reset_index(drop=True)
