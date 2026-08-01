"""Outputs: per-trade table (CSV/Excel), charts, and a self-contained HTML summary."""
from __future__ import annotations

import base64
import io
import logging
import math
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: never try to open a window
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from excursion_analyzer import TradeAnalysis  # noqa: E402
from models import CloseReason, Side  # noqa: E402
from optimizer import (  # noqa: E402
    MAX_TIMEOUT_SHARE,
    best_scenario,
    overall_mfe_r,
    trade_key,
)

log = logging.getLogger(__name__)
NAN = float("nan")

PALETTE = {
    "fg": "#1f2933",
    "muted": "#7b8794",
    "grid": "#e4e7eb",
    "long": "#2f855a",
    "short": "#c53030",
    "tp": "#2b6cb0",
    "sl": "#c05621",
    "accent": "#553c9a",
}


def _ts(ms: int) -> str:
    if not ms:
        return ""
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _round(value: float, digits: int = 6) -> float:
    return round(value, digits) if isinstance(value, float) and math.isfinite(value) else value


# ------------------------------------------------------------- trade table


def build_trade_table(analyses: list[TradeAnalysis]) -> pd.DataFrame:
    rows = []
    for a in analyses:
        trade = a.trade
        pos = trade.position
        ext = a.extension
        rows.append(
            {
                "posId": pos.pos_id,
                "instId": pos.inst_id,
                "instType": pos.inst_type,
                "posSide": trade.side.value,
                "lever": pos.lever,
                "entry": _round(trade.entry),
                "tpPx": _round(trade.tp_px),
                "slPx": _round(trade.sl_px),
                "closePx": _round(pos.close_avg_px),
                "closeReason": trade.close_reason.value,
                "classificationBasis": trade.classification_basis,
                "openTime": _ts(pos.open_time),
                "closeTime": _ts(pos.close_time),
                "holdHours": _round((pos.close_time - pos.open_time) / 3_600_000, 3),
                "realizedPnl": pos.realized_pnl,
                "pnl_priceOnly": pos.pnl,
                "riskPerUnit_1R": _round(trade.risk_per_unit),
                "rewardPerUnit": _round(trade.reward_per_unit),
                "plannedRR": _round(
                    trade.reward_per_unit / trade.risk_per_unit
                    if math.isfinite(trade.risk_per_unit) and trade.risk_per_unit > 0
                    else NAN
                ),
                "atr": _round(a.atr),
                # entry -> close
                "preClose_MFE_px": _round(a.pre_close_mfe.price),
                "preClose_MFE_R": _round(a.pre_close_mfe.r, 4),
                "preClose_MFE_time": _ts(a.pre_close_mfe.ts),
                "preClose_MAE_px": _round(a.pre_close_mae.price),
                "preClose_MAE_R": _round(a.pre_close_mae.r, 4),
                "preClose_MAE_%ofSLdistance": _round(a.mae_pct_of_sl_distance, 2),
                "MFE_%ofTPdistance": _round(a.mfe_pct_of_tp_distance, 2),
                # after close
                "postClose_MFE_px": _round(ext.excursion.price),
                "postClose_MFE_R": _round(ext.excursion.r, 4),
                "postClose_MFE_time": _ts(ext.excursion.ts),
                "postClose_extra_R": _round(a.post_close_extra_r, 4),
                "postClose_extra_%": _round(a.post_close_extra_pct, 3),
                "postClose_worstGiveback_px": _round(ext.adverse.price),
                "extensionHours": _round(ext.observed_hours, 2),
                "extensionStopReason": ext.stop_reason,
                # SL reversal study
                "wouldHaveReversed": a.would_have_reversed,
                "timeToReversal_h": _round(
                    a.time_to_reversal_ms / 3_600_000 if a.time_to_reversal_ms else NAN, 3
                ),
                "reversalDrawdown_R": _round(a.reversal_drawdown_r, 4),
                "notes": a.notes,
            }
        )
    return pd.DataFrame(rows)


# ------------------------------------------------------------------- charts


def _fig_to_b64(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def _style(ax: plt.Axes, title: str, xlabel: str = "", ylabel: str = "") -> None:
    ax.set_title(title, color=PALETTE["fg"], fontsize=11, weight="bold")
    ax.set_xlabel(xlabel, color=PALETTE["muted"], fontsize=9)
    ax.set_ylabel(ylabel, color=PALETTE["muted"], fontsize=9)
    ax.grid(True, color=PALETTE["grid"], linewidth=0.7)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.tick_params(colors=PALETTE["muted"], labelsize=8)


def chart_excursion_histograms(frame: pd.DataFrame) -> str | None:
    specs = [
        ("preClose_MFE_R", "MFE before close (R)", PALETTE["long"]),
        ("preClose_MAE_R", "MAE before close (R)", PALETTE["short"]),
        ("postClose_extra_R", "Extra move after TP/SL (R)", PALETTE["accent"]),
        ("MAE_%ofSLdistance", "Share of stop distance used (%)", PALETTE["sl"]),
    ]
    available = [s for s in specs if s[0] in frame and frame[s[0]].notna().any()]
    if not available:
        return None

    fig, axes = plt.subplots(2, 2, figsize=(11, 7))
    for ax, (col, label, color) in zip(axes.ravel(), available):
        series = pd.to_numeric(frame[col], errors="coerce").dropna()
        if series.empty:
            ax.axis("off")
            continue
        ax.hist(series, bins=min(30, max(6, len(series) // 2)), color=color, alpha=0.8,
                edgecolor="white", linewidth=0.6)
        median = series.median()
        ax.axvline(median, color=PALETTE["fg"], linestyle="--", linewidth=1.2,
                   label=f"median {median:.2f}")
        ax.legend(frameon=False, fontsize=8)
        _style(ax, label, ylabel="trades")
    for ax in axes.ravel()[len(available):]:
        ax.axis("off")
    fig.suptitle("Excursion distributions", fontsize=13, weight="bold", color=PALETTE["fg"])
    fig.tight_layout()
    return _fig_to_b64(fig)


def chart_tp_sweep(sweep: pd.DataFrame) -> str | None:
    if sweep.empty:
        return None
    fig, ax1 = plt.subplots(figsize=(9, 4.6))
    ax1.plot(sweep["tp_target_R"], sweep["expectancy_R"], color=PALETTE["accent"],
             linewidth=2, label="expectancy (R)")
    _style(ax1, "Expectancy vs TP distance", "TP target (R)", "expectancy (R)")
    ax1.axhline(0, color=PALETTE["muted"], linewidth=0.8)

    best = sweep.loc[sweep["expectancy_R"].idxmax()]
    ax1.axvline(best["tp_target_R"], color=PALETTE["tp"], linestyle="--", linewidth=1.2,
                label=f"best {best['tp_target_R']:.2f}R")

    ax2 = ax1.twinx()
    ax2.plot(sweep["tp_target_R"], sweep["hit_rate_%"], color=PALETTE["muted"],
             linewidth=1.4, linestyle=":", label="hit rate (%)")
    ax2.set_ylabel("hit rate (%)", color=PALETTE["muted"], fontsize=9)
    ax2.tick_params(colors=PALETTE["muted"], labelsize=8)
    ax2.spines["top"].set_visible(False)

    # Only lines we explicitly labelled — axhline/axvline helpers get '_child' names.
    lines = [
        line
        for line in (*ax1.get_lines(), *ax2.get_lines())
        if not str(line.get_label()).startswith("_")
    ]
    ax1.legend(lines, [l.get_label() for l in lines], frameon=False, fontsize=8, loc="lower left")
    fig.tight_layout()
    return _fig_to_b64(fig)


def chart_current_vs_suggested(frame: pd.DataFrame) -> str | None:
    data = frame.dropna(subset=["plannedRR"]) if "plannedRR" in frame else pd.DataFrame()
    if data.empty:
        return None
    mfe = pd.to_numeric(data.get("overall_MFE_R", data.get("preClose_MFE_R")), errors="coerce")
    planned = pd.to_numeric(data["plannedRR"], errors="coerce")
    mask = mfe.notna() & planned.notna()
    if not mask.any():
        return None

    fig, ax = plt.subplots(figsize=(7.5, 6))
    colors = [
        PALETTE["long"] if s == Side.LONG.value else PALETTE["short"]
        for s in data.loc[mask, "posSide"]
    ]
    ax.scatter(planned[mask], mfe[mask], c=colors, alpha=0.7, s=38, edgecolor="white",
               linewidth=0.5)
    top = float(max(planned[mask].max(), mfe[mask].max())) * 1.1
    ax.plot([0, top], [0, top], color=PALETTE["muted"], linestyle="--", linewidth=1)
    ax.text(top * 0.55, top * 0.9, "above the line = TP left money behind",
            color=PALETTE["muted"], fontsize=8)
    _style(ax, "Planned target vs. what price actually offered",
           "planned reward:risk (R)", "realised MFE (R)")
    fig.tight_layout()
    return _fig_to_b64(fig)


def chart_trade_paths(
    analyses: list[TradeAnalysis],
    candles_by_trade: dict[str, pd.DataFrame],
    limit: int = 6,
) -> str | None:
    """Price path per trade: entry -> TP/SL -> extension window."""
    picks = [
        a
        for a in analyses
        if a.trade.close_reason in (CloseReason.TP_HIT, CloseReason.SL_HIT)
        and candles_by_trade.get(trade_key(a)) is not None
        and not candles_by_trade[trade_key(a)].empty
    ][:limit]
    if not picks:
        return None

    cols = 2
    rows = math.ceil(len(picks) / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(12, 3.4 * rows), squeeze=False)

    for ax, analysis in zip(axes.ravel(), picks):
        trade = analysis.trade
        pos = trade.position
        candles = candles_by_trade[trade_key(analysis)]
        end = analysis.extension.window_end_ts or pos.close_time
        path = candles[(candles["ts"] >= pos.open_time) & (candles["ts"] <= end)]
        if path.empty:
            ax.axis("off")
            continue

        hours = (path["ts"] - pos.open_time) / 3_600_000
        ax.plot(hours, path["close"], color=PALETTE["fg"], linewidth=1.1)
        ax.axhline(trade.entry, color=PALETTE["muted"], linewidth=1, label="entry")
        if math.isfinite(trade.tp_px):
            ax.axhline(trade.tp_px, color=PALETTE["tp"], linestyle="--", linewidth=1, label="TP")
        if math.isfinite(trade.sl_px):
            ax.axhline(trade.sl_px, color=PALETTE["sl"], linestyle="--", linewidth=1, label="SL")

        close_h = (pos.close_time - pos.open_time) / 3_600_000
        ax.axvline(close_h, color=PALETTE["accent"], linewidth=1.2, alpha=0.8)
        ext = analysis.extension.excursion
        if math.isfinite(ext.price) and ext.ts:
            ax.scatter([(ext.ts - pos.open_time) / 3_600_000], [ext.price],
                       color=PALETTE["accent"], s=42, zorder=5, label="post-close MFE")

        _style(
            ax,
            f"{pos.inst_id} {trade.side.value} — {trade.close_reason.value}",
            "hours from entry",
            "price",
        )
        ax.legend(frameon=False, fontsize=7)

    for ax in axes.ravel()[len(picks):]:
        ax.axis("off")
    fig.suptitle("Trade paths: entry → exit → extension", fontsize=13, weight="bold",
                 color=PALETTE["fg"])
    fig.tight_layout()
    return _fig_to_b64(fig)


# --------------------------------------------------------------- HTML report

_CSS = """
:root { color-scheme: light dark; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       margin: 0; padding: 2rem; background: #f7f9fb; color: #1f2933; line-height: 1.55; }
.wrap { max-width: 1180px; margin: 0 auto; }
h1 { font-size: 1.6rem; margin-bottom: .25rem; }
h2 { font-size: 1.15rem; margin-top: 2.2rem; border-bottom: 2px solid #e4e7eb;
     padding-bottom: .35rem; }
.sub { color: #7b8794; font-size: .9rem; margin-top: 0; }
.cards { display: flex; flex-wrap: wrap; gap: .75rem; margin: 1.25rem 0; }
.card { background: #fff; border: 1px solid #e4e7eb; border-radius: 10px; padding: .8rem 1.1rem;
        min-width: 140px; flex: 1 1 140px; }
.card .label { font-size: .72rem; text-transform: uppercase; letter-spacing: .05em;
               color: #7b8794; }
.card .value { font-size: 1.45rem; font-weight: 600; margin-top: .15rem; }
.tablewrap { overflow-x: auto; background: #fff; border: 1px solid #e4e7eb; border-radius: 10px; }
table { border-collapse: collapse; width: 100%; font-size: .82rem; }
th, td { padding: .45rem .65rem; text-align: right; white-space: nowrap;
         border-bottom: 1px solid #eef1f4; }
th { background: #f1f4f7; font-weight: 600; text-align: right; position: sticky; top: 0; }
td:first-child, th:first-child { text-align: left; }
img { max-width: 100%; border: 1px solid #e4e7eb; border-radius: 10px; background: #fff; }
.warn { background: #fffaf0; border-left: 4px solid #dd6b20; padding: .85rem 1.1rem;
        border-radius: 6px; margin: 1rem 0; font-size: .9rem; }
.note { background: #ebf8ff; border-left: 4px solid #3182ce; padding: .85rem 1.1rem;
        border-radius: 6px; margin: 1rem 0; font-size: .9rem; }
footer { margin-top: 2.5rem; color: #7b8794; font-size: .8rem; }
@media (prefers-color-scheme: dark) {
  body { background: #12161c; color: #e4e7eb; }
  .card, .tablewrap, img { background: #1a1f27; border-color: #2c333d; }
  th { background: #222932; } td, th { border-color: #262d36; }
  h2 { border-color: #2c333d; }
  .warn { background: #2a1f12; } .note { background: #12212e; }
}
"""


def _table(frame: pd.DataFrame, max_rows: int = 60) -> str:
    if frame is None or frame.empty:
        return "<p class='sub'>No data.</p>"
    shown = frame.head(max_rows)
    html = shown.to_html(index=False, na_rep="—", float_format=lambda v: f"{v:,.4g}",
                         border=0)
    extra = (
        f"<p class='sub'>Showing {max_rows} of {len(frame)} rows — full set in the CSV.</p>"
        if len(frame) > max_rows
        else ""
    )
    return f"<div class='tablewrap'>{html}</div>{extra}"


def _img(b64: str | None, alt: str) -> str:
    if not b64:
        return f"<p class='sub'>Chart unavailable: {alt}</p>"
    return f"<img src='data:image/png;base64,{b64}' alt='{alt}'/>"


def _card(label: str, value: object) -> str:
    return f"<div class='card'><div class='label'>{label}</div><div class='value'>{value}</div></div>"


def render_html_report(
    *,
    output_path: Path,
    trade_table: pd.DataFrame,
    excursions: pd.DataFrame,
    distributions: pd.DataFrame,
    sweep: pd.DataFrame,
    scenarios: pd.DataFrame,
    scaled: pd.DataFrame,
    recommendations: pd.DataFrame,
    match_summary: dict[str, int],
    charts: dict[str, str | None],
    warnings: list[str],
    period: tuple[str, str],
) -> Path:
    tp_hits = match_summary.get("TP_HIT", 0)
    sl_hits = match_summary.get("SL_HIT", 0)
    total = match_summary.get("TOTAL", 0)

    missed = pd.to_numeric(excursions.get("postClose_extra_R"), errors="coerce").dropna()
    avg_missed = f"{missed.mean():.2f}R" if not missed.empty else "—"

    reversed_series = excursions.get("wouldHaveReversed")
    if reversed_series is not None:
        reversed_vals = reversed_series.dropna()
        rev_rate = (
            f"{(reversed_vals.astype(bool).sum() / len(reversed_vals) * 100):.0f}%"
            if len(reversed_vals)
            else "—"
        )
    else:
        rev_rate = "—"

    best_line = ""
    timeout_warning = ""
    if not scenarios.empty:
        top = best_scenario(scenarios)
        if top is not None:
            best_line = (
                f"Best scenario with enough resolved trades: <strong>TP x{top['tp_mult']}, "
                f"SL x{top['sl_mult']}</strong> → expectancy {top['expectancy_R']}R "
                f"({top['resolved_expectancy_R']}R counting only resolved trades) over "
                f"{int(top['trades'])} trades, {top['timeout_%']}% unresolved."
            )
        if not scenarios["reliable"].any():
            timeout_warning = (
                "<div class='warn'><strong>Every scenario is dominated by unresolved "
                "trades.</strong> With a wider TP, most positions never reach either level "
                "inside the available candle window, so their result is just the price at "
                "the end of the window. Treat this whole grid as indicative only, and "
                "re-run with a larger <code>--max-hours</code> for firmer numbers.</div>"
            )
        elif (~scenarios["reliable"]).any():
            unreliable = int((~scenarios["reliable"]).sum())
            timeout_warning = (
                f"<div class='note'>{unreliable} of {len(scenarios)} scenarios had more than "
                f"{int(MAX_TIMEOUT_SHARE * 100)}% unresolved trades and are marked "
                f"<code>reliable = False</code>. Their expectancy mostly reflects marking open "
                f"trades to the end of the data, not the TP/SL rule — they are sorted below "
                f"the reliable ones.</div>"
            )

    warn_html = "".join(f"<div class='warn'>{w}</div>" for w in warnings)
    dist_table = (
        distributions.reset_index().rename(columns={"index": "metric"})
        if not distributions.empty
        else distributions
    )

    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OKX TP/SL Excursion Report</title><style>{_CSS}</style></head>
<body><div class="wrap">
<h1>OKX TP/SL excursion &amp; optimisation report</h1>
<p class="sub">Analysis period {period[0]} → {period[1]} · generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC</p>

{warn_html}

<div class="cards">
  {_card("Positions", total)}
  {_card("TP hits", tp_hits)}
  {_card("SL hits", sl_hits)}
  {_card("Manual / other", total - tp_hits - sl_hits)}
  {_card("Avg. move after exit", avg_missed)}
  {_card("SL trades that later hit TP", rev_rate)}
</div>

<div class="note"><strong>How to read this.</strong> 1R is the entry-to-stop distance of each
trade, so every R figure is risk-normalised and comparable across symbols. "Move after exit"
is how far price continued in the trade's direction after the position closed, measured over
the adaptive extension window.</div>

<h2>Close-reason breakdown</h2>
{_table(pd.DataFrame([match_summary]))}

<h2>Excursion distributions</h2>
{_img(charts.get("histograms"), "excursion histograms")}
{_table(dist_table)}

<h2>Expectancy vs TP distance</h2>
{_img(charts.get("sweep"), "TP sweep")}
<p class="sub">Hit rate is the share of historical trades whose favourable excursion reached
that distance. Expectancy assumes the trade otherwise loses a full 1R, and ignores intrabar
ordering — treat it as the optimistic bound and cross-check against the backtest below.</p>
{_table(sweep, max_rows=40)}

<h2>What-if backtest (bar-by-bar)</h2>
<p class="sub">{best_line}</p>
{timeout_warning}
{_table(scenarios, max_rows=40)}
<div class="note">Where a single 1-minute bar spans both the alternative TP and the alternative
SL, the stop is assumed to fill first. Results are therefore a conservative floor; the
<code>ambiguous_bars</code> column shows how often that tie-break was applied.
<br><br><strong>Unresolved trades.</strong> A trade that reaches neither level before the end of
the candle window is a <em>timeout</em>, scored at the final close. <code>R_from_timeouts</code>
shows how much of <code>total_R</code> came from those marks — when it is most of the total, the
scenario is measuring the market's drift, not your exit rule.</div>

<h2>Scaled exit study (second target)</h2>
<p class="sub">Exploratory: you do not currently use partial exits. This models taking part of
the position off at the existing TP and letting the remainder run.</p>
{_table(scaled)}

<h2>Per-symbol guidance</h2>
{_table(recommendations)}

<h2>Planned target vs realised opportunity</h2>
{_img(charts.get("scatter"), "planned vs realised")}

<h2>Trade paths</h2>
{_img(charts.get("paths"), "trade paths")}

<h2>Trades</h2>
{_table(trade_table, max_rows=80)}

<footer>
Price-action based: funding fees are excluded from all excursion maths by design.
The "SL would have reversed" figures are hypothetical hindsight — they ignore the margin and
liquidation risk of holding through that drawdown, and are not a case for trading without a stop.
</footer>
</div></body></html>"""

    output_path.write_text(html, encoding="utf-8")
    return output_path


# --------------------------------------------------------------- entry point


def write_reports(
    *,
    output_dir: Path,
    analyses: list[TradeAnalysis],
    candles_by_trade: dict[str, pd.DataFrame],
    excursions: pd.DataFrame,
    distributions: pd.DataFrame,
    sweep: pd.DataFrame,
    scenarios: pd.DataFrame,
    scaled: pd.DataFrame,
    recommendations: pd.DataFrame,
    match_summary: dict[str, int],
    warnings: list[str],
    period: tuple[str, str],
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}

    trade_table = build_trade_table(analyses)
    csv_path = output_dir / "trades.csv"
    trade_table.to_csv(csv_path, index=False)
    written["trades_csv"] = csv_path

    xlsx_path = output_dir / "analysis.xlsx"
    try:
        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
            trade_table.to_excel(writer, sheet_name="trades", index=False)
            excursions.to_excel(writer, sheet_name="excursions", index=False)
            distributions.reset_index().to_excel(writer, sheet_name="distributions", index=False)
            sweep.to_excel(writer, sheet_name="tp_sweep", index=False)
            scenarios.to_excel(writer, sheet_name="whatif", index=False)
            scaled.to_excel(writer, sheet_name="scaled_exits", index=False)
            recommendations.to_excel(writer, sheet_name="recommendations", index=False)
        written["excel"] = xlsx_path
    except Exception as exc:  # openpyxl missing or sheet error — CSV already covers it
        log.warning("Excel export skipped: %s", exc)

    merged = trade_table.copy()
    if "overall_MFE_R" in excursions and len(excursions) == len(merged):
        merged["overall_MFE_R"] = excursions["overall_MFE_R"].to_numpy()

    charts = {
        "histograms": chart_excursion_histograms(excursions),
        "sweep": chart_tp_sweep(sweep),
        "scatter": chart_current_vs_suggested(merged),
        "paths": chart_trade_paths(analyses, candles_by_trade),
    }

    html_path = render_html_report(
        output_path=output_dir / "report.html",
        trade_table=trade_table,
        excursions=excursions,
        distributions=distributions,
        sweep=sweep,
        scenarios=scenarios,
        scaled=scaled,
        recommendations=recommendations,
        match_summary=match_summary,
        charts=charts,
        warnings=warnings,
        period=period,
    )
    written["html"] = html_path
    return written
