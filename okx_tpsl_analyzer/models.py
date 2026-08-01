"""Typed views over the raw OKX payloads, plus the analysis result records."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


def _f(raw: Any, default: float = float("nan")) -> float:
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _i(raw: Any, default: int = 0) -> int:
    if raw is None or raw == "":
        return default
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return default


class CloseReason(str, Enum):
    TP_HIT = "TP_HIT"
    SL_HIT = "SL_HIT"
    MANUAL = "MANUAL"
    LIQUIDATION = "LIQUIDATION"
    ADL = "ADL"
    UNKNOWN = "UNKNOWN"


class Side(str, Enum):
    LONG = "long"
    SHORT = "short"

    @property
    def sign(self) -> int:
        """+1 when profit rises with price, -1 when it falls."""
        return 1 if self is Side.LONG else -1


@dataclass(frozen=True)
class Instrument:
    inst_id: str
    inst_type: str
    ct_type: str  # 'linear' | 'inverse' | '' (for MARGIN)
    ct_val: float
    ct_mult: float
    tick_sz: float
    settle_ccy: str

    @property
    def is_inverse(self) -> bool:
        return self.ct_type == "inverse"

    @classmethod
    def from_api(cls, row: dict[str, Any]) -> "Instrument":
        return cls(
            inst_id=row.get("instId", ""),
            inst_type=row.get("instType", ""),
            ct_type=row.get("ctType", ""),
            ct_val=_f(row.get("ctVal"), 1.0),
            ct_mult=_f(row.get("ctMult"), 1.0),
            tick_sz=_f(row.get("tickSz"), 0.0),
            settle_ccy=row.get("settleCcy", ""),
        )


@dataclass(frozen=True)
class ClosedPosition:
    pos_id: str
    inst_id: str
    inst_type: str
    mgn_mode: str
    side: Side
    lever: float
    open_avg_px: float
    close_avg_px: float
    open_max_pos: float
    close_total_pos: float
    realized_pnl: float
    pnl: float
    pnl_ratio: float
    fee: float
    funding_fee: float
    liq_penalty: float
    open_time: int  # cTime — position created
    close_time: int  # uTime — position last updated (i.e. closed)
    close_type: int  # 1 partial, 2 close-all, 3 liq, 4 partial-liq, 5/6 ADL
    trigger_px: float  # only populated for liquidation/ADL

    @classmethod
    def from_api(cls, row: dict[str, Any]) -> "ClosedPosition":
        direction = (row.get("direction") or "").lower()
        if direction not in ("long", "short"):
            # Net mode without an explicit direction: infer from the P&L sign.
            pnl = _f(row.get("pnl"), 0.0)
            opened, closed = _f(row.get("openAvgPx")), _f(row.get("closeAvgPx"))
            direction = "long" if (closed - opened) * (1 if pnl >= 0 else -1) >= 0 else "short"
        return cls(
            pos_id=str(row.get("posId", "")),
            inst_id=row.get("instId", ""),
            inst_type=row.get("instType", ""),
            mgn_mode=row.get("mgnMode", ""),
            side=Side(direction),
            lever=_f(row.get("lever"), 1.0),
            open_avg_px=_f(row.get("openAvgPx")),
            close_avg_px=_f(row.get("closeAvgPx")),
            open_max_pos=_f(row.get("openMaxPos"), 0.0),
            close_total_pos=_f(row.get("closeTotalPos"), 0.0),
            realized_pnl=_f(row.get("realizedPnl"), 0.0),
            pnl=_f(row.get("pnl"), 0.0),
            pnl_ratio=_f(row.get("pnlRatio"), 0.0),
            fee=_f(row.get("fee"), 0.0),
            funding_fee=_f(row.get("fundingFee"), 0.0),
            liq_penalty=_f(row.get("liqPenalty"), 0.0),
            open_time=_i(row.get("cTime")),
            close_time=_i(row.get("uTime")),
            close_type=_i(row.get("type")),
            trigger_px=_f(row.get("triggerPx"), float("nan")),
        )


@dataclass(frozen=True)
class AlgoOrder:
    algo_id: str
    inst_id: str
    inst_type: str
    pos_side: str
    side: str
    ord_type: str
    state: str
    tp_trigger_px: float
    tp_ord_px: float
    tp_trigger_px_type: str
    sl_trigger_px: float
    sl_ord_px: float
    sl_trigger_px_type: str
    actual_side: str  # 'tp' | 'sl' | ''
    actual_px: float
    actual_sz: float
    close_fraction: float
    sz: float
    trigger_time: int
    c_time: int
    u_time: int

    @property
    def triggered(self) -> bool:
        return self.state == "effective" and self.trigger_time > 0

    @classmethod
    def from_api(cls, row: dict[str, Any]) -> "AlgoOrder":
        return cls(
            algo_id=str(row.get("algoId", "")),
            inst_id=row.get("instId", ""),
            inst_type=row.get("instType", ""),
            pos_side=row.get("posSide", ""),
            side=row.get("side", ""),
            ord_type=row.get("ordType", ""),
            state=row.get("state", ""),
            tp_trigger_px=_f(row.get("tpTriggerPx")),
            tp_ord_px=_f(row.get("tpOrdPx")),
            tp_trigger_px_type=row.get("tpTriggerPxType", "") or "last",
            sl_trigger_px=_f(row.get("slTriggerPx")),
            sl_ord_px=_f(row.get("slOrdPx")),
            sl_trigger_px_type=row.get("slTriggerPxType", "") or "last",
            actual_side=(row.get("actualSide") or "").lower(),
            actual_px=_f(row.get("actualPx")),
            actual_sz=_f(row.get("actualSz"), 0.0),
            close_fraction=_f(row.get("closeFraction"), float("nan")),
            sz=_f(row.get("sz"), 0.0),
            trigger_time=_i(row.get("triggerTime")),
            c_time=_i(row.get("cTime")),
            u_time=_i(row.get("uTime")),
        )


@dataclass
class MatchedTrade:
    """A closed position joined to the TP/SL levels that governed it."""

    position: ClosedPosition
    instrument: Instrument | None
    tp_px: float = float("nan")
    sl_px: float = float("nan")
    close_reason: CloseReason = CloseReason.UNKNOWN
    classification_basis: str = ""  # how we decided — for auditability
    algo_orders: list[AlgoOrder] = field(default_factory=list)
    triggering_algo: AlgoOrder | None = None

    @property
    def entry(self) -> float:
        return self.position.open_avg_px

    @property
    def side(self) -> Side:
        return self.position.side

    @property
    def risk_per_unit(self) -> float:
        """1R in price terms — the entry-to-stop distance."""
        if self.sl_px != self.sl_px:  # NaN
            return float("nan")
        return abs(self.entry - self.sl_px)

    @property
    def reward_per_unit(self) -> float:
        if self.tp_px != self.tp_px:
            return float("nan")
        return abs(self.tp_px - self.entry)
