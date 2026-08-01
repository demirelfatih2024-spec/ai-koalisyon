"""Thin, typed OKX v5 REST client.

Why raw ``requests`` instead of ccxt: the three endpoints this project depends on
(``positions-history``, ``orders-algo-history``, ``history-candles``) are either not
exposed by ccxt's unified API at all, or lose the OKX-specific fields we need most —
``actualSide``, ``tpTriggerPxType``, ``posId``, ``closeTotalPos``. Using ccxt would mean
falling back to its ``implicit`` passthrough anyway, which buys the maintenance burden
without the abstraction benefit. So: native requests + our own signing.

Endpoint semantics verified against https://www.okx.com/docs-v5/en/ (July 2026):

* ``GET /api/v5/account/positions-history`` — last **3 months** only. Reverse-chronological
  by ``uTime``. ``after``/``before`` page by ``uTime``. limit max 100. 10 req / 2 s.
* ``GET /api/v5/trade/orders-algo-history`` — last **3 months** only. ``ordType`` is
  required (``conditional`` and ``oco`` may be comma-joined); **either ``state`` or
  ``algoId`` is required**. ``after``/``before`` page by **algoId**, not by time.
  limit max 100. 20 req / 2 s.
* ``GET /api/v5/market/history-candles`` — limit max **300** (not 100). Returns
  newest-first. ``after=ts`` pages backwards into history; ``before=ts`` returns the
  *latest* candles newer than ts rather than the ones immediately following it, so
  backward paging via ``after`` is the only reliable backfill cursor.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Iterable, Sequence
from urllib.parse import urlencode

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import Credentials

log = logging.getLogger(__name__)

# OKX error codes that are worth retrying rather than surfacing.
_RETRYABLE_OKX_CODES = {"50011", "50013", "50026"}  # rate limit, busy, system error

# Credential/signature/permission failures. These must never be swallowed as "this
# query simply had no records" — otherwise a bad key looks like an empty account.
_FATAL_AUTH_CODES = {
    "401",
    "50100",
    "50101",
    "50102",  # timestamp expired
    "50103",  # missing signature header
    "50104",
    "50105",  # passphrase incorrect
    "50111",  # invalid API key
    "50112",
    "50113",  # invalid signature
    "50114",
}


class OKXError(RuntimeError):
    """Non-retryable API-level error (OKX returned code != '0')."""

    def __init__(self, code: str, msg: str, path: str) -> None:
        super().__init__(f"OKX {path} failed: code={code} msg={msg!r}")
        self.code = code
        self.msg = msg


class OKXRetryableError(RuntimeError):
    """Transient failure — HTTP 5xx/429 or a retryable OKX business code."""


class RateLimiter:
    """Simple sliding-window limiter: at most ``n`` calls per ``per_seconds``."""

    def __init__(self, n: int, per_seconds: float) -> None:
        self._n = n
        self._per = per_seconds
        self._calls: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                while self._calls and now - self._calls[0] > self._per:
                    self._calls.popleft()
                if len(self._calls) < self._n:
                    self._calls.append(now)
                    return
                sleep_for = self._per - (now - self._calls[0]) + 0.01
            time.sleep(max(sleep_for, 0.01))


def _iso_timestamp() -> str:
    """OKX wants ISO8601 with exactly milliseconds and a trailing Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class OKXClient:
    def __init__(
        self,
        credentials: Credentials,
        base_url: str = "https://www.okx.com",
        timeout: float = 30.0,
    ) -> None:
        self._creds = credentials
        self._base = base_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        # Conservative shared limits; the tightest documented bucket is 10 req/2s.
        self._private_limiter = RateLimiter(8, 2.0)
        self._public_limiter = RateLimiter(15, 2.0)

    # ---------------------------------------------------------------- signing

    def _sign(self, ts: str, method: str, request_path: str, body: str = "") -> str:
        msg = f"{ts}{method.upper()}{request_path}{body}"
        mac = hmac.new(
            self._creds.api_secret.encode(), msg.encode(), hashlib.sha256
        ).digest()
        return base64.b64encode(mac).decode()

    def _headers(self, method: str, request_path: str, body: str = "") -> dict[str, str]:
        ts = _iso_timestamp()
        headers = {
            "OK-ACCESS-KEY": self._creds.api_key,
            "OK-ACCESS-SIGN": self._sign(ts, method, request_path, body),
            "OK-ACCESS-TIMESTAMP": ts,
            "OK-ACCESS-PASSPHRASE": self._creds.passphrase,
            "Content-Type": "application/json",
        }
        if self._creds.simulated:
            headers["x-simulated-trading"] = "1"
        return headers

    # ------------------------------------------------------------- transport

    @retry(
        retry=retry_if_exception_type(
            (OKXRetryableError, requests.RequestException)
        ),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=0.6, min=0.6, max=20),
        reraise=True,
    )
    def _request(
        self, path: str, params: dict[str, Any] | None = None, private: bool = True
    ) -> list[dict[str, Any]]:
        clean = {k: str(v) for k, v in (params or {}).items() if v not in (None, "")}
        query = urlencode(clean)
        request_path = f"{path}?{query}" if query else path
        url = f"{self._base}{request_path}"

        (self._private_limiter if private else self._public_limiter).acquire()

        headers = self._headers("GET", request_path) if private else {}
        resp = self._session.get(url, headers=headers, timeout=self._timeout)

        if resp.status_code == 429 or resp.status_code >= 500:
            raise OKXRetryableError(f"HTTP {resp.status_code} on {request_path}")
        if resp.status_code == 401:
            raise OKXError("401", "Unauthorized — check API key/secret/passphrase", path)
        resp.raise_for_status()

        payload = resp.json()
        code = str(payload.get("code", ""))
        if code != "0":
            if code in _RETRYABLE_OKX_CODES:
                raise OKXRetryableError(f"OKX code {code}: {payload.get('msg')}")
            raise OKXError(code, str(payload.get("msg", "")), path)
        return payload.get("data", []) or []

    # ------------------------------------------------------------ public API

    def get_instruments(self, inst_type: str) -> list[dict[str, Any]]:
        """Instrument metadata: tickSz, ctVal, ctType (linear/inverse), settleCcy."""
        return self._request(
            "/api/v5/public/instruments", {"instType": inst_type}, private=False
        )

    def get_history_candles(
        self, inst_id: str, bar: str, after_ms: int | None = None, limit: int = 300
    ) -> list[list[str]]:
        """One page of candles, newest-first. ``after_ms`` pages backwards."""
        data = self._request(
            "/api/v5/market/history-candles",
            {"instId": inst_id, "bar": bar, "after": after_ms, "limit": limit},
            private=False,
        )
        return data  # type: ignore[return-value]

    # ----------------------------------------------------------- private API

    def get_positions_history(
        self,
        inst_type: str | None = None,
        start_ms: int | None = None,
        end_ms: int | None = None,
        inst_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """All closed positions in [start_ms, end_ms], paging backwards by ``uTime``.

        Only the trailing ~3 months exist server-side regardless of what is asked for.
        """
        out: list[dict[str, Any]] = []
        seen: set[str] = set()
        cursor = end_ms
        while True:
            page = self._request(
                "/api/v5/account/positions-history",
                {
                    "instType": inst_type,
                    "instId": inst_id,
                    "after": cursor,
                    "limit": 100,
                },
            )
            if not page:
                break

            oldest = None
            fresh = 0
            for row in page:
                utime = int(row.get("uTime") or 0)
                oldest = utime if oldest is None else min(oldest, utime)
                key = f"{row.get('posId')}:{row.get('uTime')}"
                if key in seen:
                    continue
                seen.add(key)
                if start_ms is not None and utime < start_ms:
                    continue
                if end_ms is not None and utime > end_ms:
                    continue
                out.append(row)
                fresh += 1

            log.debug(
                "positions-history page: %d rows (%d kept), oldest uTime=%s",
                len(page),
                fresh,
                oldest,
            )
            if len(page) < 100 or oldest is None:
                break
            if start_ms is not None and oldest < start_ms:
                break
            # Step strictly past the oldest row to avoid an infinite loop when
            # many rows share a uTime (OKX returns all ties in one page).
            cursor = oldest - 1
        return out

    def get_algo_order_history(
        self,
        ord_types: Sequence[str] = ("conditional", "oco"),
        states: Iterable[str] = ("effective", "canceled", "order_failed"),
        inst_type: str | None = None,
        inst_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Algo (TP/SL) order history.

        ``ordType`` is mandatory and ``conditional``/``oco`` may be comma-joined, but
        *either* ``state`` or ``algoId`` must also be supplied — so we loop over states.
        Pagination here is by **algoId**, not by timestamp.
        """
        ord_type = ",".join(ord_types)
        out: list[dict[str, Any]] = []
        seen: set[str] = set()
        states = list(states)
        last_error: OKXError | None = None
        succeeded = False

        for state in states:
            cursor: str | None = None
            while True:
                try:
                    page = self._request(
                        "/api/v5/trade/orders-algo-history",
                        {
                            "ordType": ord_type,
                            "state": state,
                            "instType": inst_type,
                            "instId": inst_id,
                            "after": cursor,
                            "limit": 100,
                        },
                    )
                except OKXError as exc:
                    # Never mask a bad key as an empty result set.
                    if exc.code in _FATAL_AUTH_CODES:
                        raise
                    # A state the account has no records for can 400 on some tenants.
                    log.warning("algo history state=%s skipped: %s", state, exc)
                    last_error = exc
                    break
                succeeded = True
                if not page:
                    break

                smallest_algo_id: int | None = None
                for row in page:
                    algo_id = str(row.get("algoId", ""))
                    if algo_id and algo_id not in seen:
                        seen.add(algo_id)
                        out.append(row)
                    if algo_id.isdigit():
                        n = int(algo_id)
                        smallest_algo_id = n if smallest_algo_id is None else min(
                            smallest_algo_id, n
                        )

                if len(page) < 100 or smallest_algo_id is None:
                    break
                cursor = str(smallest_algo_id)

        # Every state failed: that is an error, not an empty account.
        if not succeeded and last_error is not None:
            raise last_error
        return out
