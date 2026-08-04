"""CLI orchestration.

    python main.py --start 2026-05-01 --end 2026-07-31
    python main.py --start 2026-05-01 --end 2026-07-31 --symbols BTC-USDT-SWAP,ETH-USDT-SWAP
    python main.py --demo                      # synthetic data, no API key needed

Note on history depth: OKX serves only the trailing ~3 months of positions-history and
orders-algo-history. A --start older than that returns nothing for the missing span; the
run warns and continues with whatever the API actually holds.
"""
from __future__ import annotations

import argparse
import logging
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from candle_fetcher import CandleFetcher, average_true_range, resample_ohlc
from config import API_HISTORY_RETENTION_DAYS, load_settings
from demo_data import build_demo
from excursion_analyzer import HOUR_MS, analyze_trade
from models import AlgoOrder, ClosedPosition, Instrument
from okx_client import OKXClient, OKXError
from optimizer import (
    best_scenario,
    describe_distributions,
    excursion_frame,
    recommend_levels,
    scaled_exit_study,
    tp_sweep,
    trade_key,
    whatif_backtest,
)
from report_generator import write_reports
from trade_matcher import match_trades, summarize_matching

log = logging.getLogger("okx_tpsl")


def parse_date(text: str, end_of_day: bool = False) -> int:
    dt = datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if end_of_day:
        dt += timedelta(days=1) - timedelta(milliseconds=1)
    return int(dt.timestamp() * 1000)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Analyse OKX futures TP/SL accuracy via MFE/MAE excursions.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--start", help="inclusive start date, YYYY-MM-DD")
    p.add_argument("--end", help="inclusive end date, YYYY-MM-DD")
    p.add_argument("--symbols", default="", help="comma-separated instIds; empty = all")
    p.add_argument(
        "--inst-types",
        default="SWAP,FUTURES",
        help="OKX instrument types to scan (SWAP, FUTURES, MARGIN)",
    )
    p.add_argument("--bar", default=None, help="candle granularity (default from .env: 1m)")
    p.add_argument("--output", default=None, help="output directory")
    p.add_argument("--demo", action="store_true", help="run on synthetic data, no API key")
    p.add_argument("--max-hours", type=float, default=None, help="override extension cap")
    p.add_argument(
        "--rejim",
        default="all",
        choices=["all", "guncel", "kismi_duzeltme", "duzeltme_oncesi"],
        help="GÖREV 1.1: whatif/tp_sweep/dist/recommendations'ı sadece bu kod rejimindeki "
             "işlemlerden hesapla ('guncel' = tüm düzeltmeler yürürlükteyken açılanlar)",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    return p


def _dedupe_positions(rows: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out = []
    for row in rows:
        key = f"{row.get('posId')}:{row.get('uTime')}"
        if key not in seen:
            seen.add(key)
            out.append(row)
    return out


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    settings = load_settings()
    settings.ensure_dirs()
    output_dir = Path(args.output) if args.output else settings.output_dir
    bar = args.bar or settings.bar
    ext_cfg = settings.extension
    if args.max_hours is not None:
        ext_cfg = type(ext_cfg)(
            min_hours=ext_cfg.min_hours,
            max_hours=args.max_hours,
            retrace_atr_mult=ext_cfg.retrace_atr_mult,
            retrace_pct_fallback=ext_cfg.retrace_pct_fallback,
            retrace_basis=ext_cfg.retrace_basis,
        )

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_ms = parse_date(args.start) if args.start else now_ms - 89 * 86_400_000
    end_ms = parse_date(args.end, end_of_day=True) if args.end else now_ms
    if start_ms >= end_ms:
        log.error("--start must be earlier than --end")
        return 2

    warnings: list[str] = []
    retention_floor = now_ms - API_HISTORY_RETENTION_DAYS * 86_400_000
    if not args.demo and start_ms < retention_floor:
        floor_date = datetime.fromtimestamp(retention_floor / 1000, timezone.utc).date()
        msg = (
            f"<strong>History limit:</strong> OKX only serves the last "
            f"{API_HISTORY_RETENTION_DAYS} days of position and algo-order history. "
            f"Data before {floor_date} cannot be retrieved from the API, so the effective "
            f"start of this analysis is {floor_date} regardless of --start."
        )
        warnings.append(msg)
        log.warning(
            "requested start predates OKX's %d-day retention; effective start is %s",
            API_HISTORY_RETENTION_DAYS,
            floor_date,
        )

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    inst_types = [s.strip().upper() for s in args.inst_types.split(",") if s.strip()]

    # ---------------------------------------------------------- data sourcing
    demo_candles: dict[str, pd.DataFrame] = {}
    if args.demo:
        log.info("running in demo mode with synthetic data")
        pos_raw, algo_raw, inst_raw, demo_candles = build_demo()
        warnings.append(
            "<strong>Demo mode:</strong> every figure below comes from synthetic data and "
            "describes nothing about a real account."
        )
        start_ms = min(int(p["cTime"]) for p in pos_raw)
        end_ms = max(int(p["uTime"]) for p in pos_raw)
    else:
        if not settings.credentials.is_complete:
            log.error(
                "Missing credentials. Copy .env.example to .env and fill in "
                "OKX_API_KEY / OKX_API_SECRET / OKX_API_PASSPHRASE, or run with --demo."
            )
            return 2
        client = OKXClient(settings.credentials, settings.base_url)

        pos_raw, algo_raw, inst_raw = [], [], []
        for inst_type in inst_types:
            log.info("fetching %s positions history...", inst_type)
            try:
                pos_raw.extend(
                    client.get_positions_history(
                        inst_type=inst_type, start_ms=start_ms, end_ms=end_ms
                    )
                )
                algo_raw.extend(client.get_algo_order_history(inst_type=inst_type))
                inst_raw.extend(client.get_instruments(inst_type))
            except OKXError as exc:
                log.error("%s skipped: %s", inst_type, exc)
        pos_raw = _dedupe_positions(pos_raw)

    positions = [ClosedPosition.from_api(r) for r in pos_raw]
    if symbols:
        positions = [p for p in positions if p.inst_id in symbols]
    positions = [p for p in positions if start_ms <= p.close_time <= end_ms]
    positions.sort(key=lambda p: p.close_time)

    if not positions:
        log.error(
            "No closed positions found in %s..%s. If the range is older than %d days, "
            "that is expected — see the history limit note.",
            datetime.fromtimestamp(start_ms / 1000, timezone.utc).date(),
            datetime.fromtimestamp(end_ms / 1000, timezone.utc).date(),
            API_HISTORY_RETENTION_DAYS,
        )
        return 1

    algo_orders = [AlgoOrder.from_api(r) for r in algo_raw]
    instruments = {i.inst_id: i for i in (Instrument.from_api(r) for r in inst_raw)}
    log.info(
        "%d closed positions, %d algo orders, %d instruments",
        len(positions),
        len(algo_orders),
        len(instruments),
    )

    # ------------------------------------------------------------- matching
    trades = match_trades(positions, algo_orders, instruments, settings.match)
    match_summary = summarize_matching(trades)
    log.info("close reasons: %s", match_summary)
    if match_summary.get("WITH_TP_LEVEL", 0) == 0 and not args.demo:
        warnings.append(
            "<strong>No TP/SL levels recovered.</strong> Algo-order history returned nothing "
            "usable for these positions — likely because the orders fall outside OKX's "
            "3-month retention. Excursion figures are still valid, but R-multiples and the "
            "optimiser need a stop distance and will be mostly empty."
        )

    # -------------------------------------------------------------- candles
    pad_ms = int(settings.pre_entry_pad_hours * HOUR_MS)
    ext_ms = int(ext_cfg.max_hours * HOUR_MS)
    needed: dict[str, list[tuple[int, int]]] = {}
    for trade in trades:
        pos = trade.position
        needed.setdefault(pos.inst_id, []).append(
            (pos.open_time - pad_ms, pos.close_time + ext_ms)
        )

    candles_by_trade: dict[str, pd.DataFrame] = {}
    if args.demo:
        store = demo_candles
    else:
        fetcher = CandleFetcher(client, settings.cache_dir, bar=bar)
        store = {}
        for inst_id, ranges in needed.items():
            try:
                fetcher.ensure(inst_id, ranges)
            except Exception as exc:
                log.warning("candle fetch failed for %s: %s", inst_id, exc)
            lo = min(r[0] for r in ranges)
            hi = max(r[1] for r in ranges)
            store[inst_id] = fetcher.get(inst_id, lo, hi)

    # ------------------------------------------------------------- analysis
    analyses = []
    for trade in trades:
        pos = trade.position
        full = store.get(pos.inst_id, pd.DataFrame())
        if full.empty:
            window = full
            atr = float("nan")
        else:
            window = full[
                (full["ts"] >= pos.open_time - pad_ms)
                & (full["ts"] <= pos.close_time + ext_ms)
            ].reset_index(drop=True)
            warmup = window[window["ts"] <= pos.open_time]
            hourly = resample_ohlc(warmup, "1h")
            atr = average_true_range(hourly, settings.atr_period)
            if not math.isfinite(atr) or atr <= 0:
                atr = float("nan")
        analyses.append(analyze_trade(trade, window, ext_cfg, atr=atr))
        candles_by_trade[trade_key(analyses[-1])] = window

    # ── GÖREV 1.1: rejim filtresi ────────────────────────────────────────────
    # whatif/tp_sweep/distributions/recommendations, seçilen rejimdeki işlemlerden
    # hesaplanır. trades.csv HER ZAMAN tüm işlemleri (kod_rejimi kolonuyla) içerir.
    from report_generator import kod_rejimi as _kod_rejimi
    _rejim_dagilimi = {}
    for a in analyses:
        _r = _kod_rejimi(a.trade.position.open_time)
        _rejim_dagilimi[_r] = _rejim_dagilimi.get(_r, 0) + 1
    log.info("kod rejimi dağılımı: %s", _rejim_dagilimi)
    if args.rejim != "all":
        analyses_opt = [a for a in analyses if _kod_rejimi(a.trade.position.open_time) == args.rejim]
        log.info("rejim filtresi '%s': %d/%d işlem seçildi", args.rejim, len(analyses_opt), len(analyses))
        if not analyses_opt:
            log.error("'%s' rejiminde işlem yok — çıkılıyor.", args.rejim)
            return 1
        if len(analyses_opt) < 15:
            warnings.append(
                f"<strong>⚠️ Örneklem küçük:</strong> '{args.rejim}' rejiminde yalnızca "
                f"{len(analyses_opt)} işlem var. whatif/tp_sweep/öneriler istatistiksel olarak "
                f"güvenilir değil — yön verici, kesin değil."
            )
    else:
        analyses_opt = analyses   # 'all': optimizer tüm işlemler üzerinde

    # ----------------------------------------------------------- optimising
    # NOT: trades tablosu HER ZAMAN tüm işlemleri (kod_rejimi kolonuyla) içerir;
    # yalnızca aşağıdaki optimizasyon tabloları rejime göre filtrelenmiş 'analyses_opt' kullanır.
    excursions = excursion_frame(analyses_opt)
    distributions = describe_distributions(excursions)
    sweep = tp_sweep(analyses_opt)
    scenarios, _ = whatif_backtest(
        analyses_opt,
        candles_by_trade,
        tp_mults=settings.whatif_tp_mults,
        sl_mults=settings.whatif_sl_mults,
        max_hours=ext_cfg.max_hours,
    )
    scaled = scaled_exit_study(
        analyses_opt, candles_by_trade, max_hours=ext_cfg.max_hours
    )
    recommendations = recommend_levels(excursions)

    # ------------------------------------------------------------ reporting
    period = (
        datetime.fromtimestamp(start_ms / 1000, timezone.utc).strftime("%Y-%m-%d"),
        datetime.fromtimestamp(end_ms / 1000, timezone.utc).strftime("%Y-%m-%d"),
    )
    written = write_reports(
        output_dir=output_dir,
        analyses=analyses,
        candles_by_trade=candles_by_trade,
        excursions=excursions,
        distributions=distributions,
        sweep=sweep,
        scenarios=scenarios,
        scaled=scaled,
        recommendations=recommendations,
        match_summary=match_summary,
        warnings=warnings,
        period=period,
    )

    print("\n=== Close reasons ===")
    for key, value in match_summary.items():
        print(f"  {key:<16} {value}")

    if not sweep.empty:
        best = sweep.loc[sweep["expectancy_R"].idxmax()]
        print(
            f"\nBest TP distance by naive expectancy: {best['tp_target_R']}R "
            f"(hit rate {best['hit_rate_%']}%, expectancy {best['expectancy_R']}R)"
        )
    top = best_scenario(scenarios)
    if top is not None:
        print(
            f"Best what-if scenario: TP x{top['tp_mult']} / SL x{top['sl_mult']} → "
            f"expectancy {top['expectancy_R']}R "
            f"({top['resolved_expectancy_R']}R on resolved trades only) "
            f"over {int(top['trades'])} trades, {top['timeout_%']}% unresolved"
        )
        if not scenarios["reliable"].any():
            print(
                "  ! Every scenario had >35% unresolved trades — their expectancy mostly\n"
                "    reflects marking open trades to the end of the data. Re-run with a\n"
                "    larger --max-hours before acting on this grid."
            )

    print("\n=== Written ===")
    for label, path in written.items():
        print(f"  {label:<12} {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
