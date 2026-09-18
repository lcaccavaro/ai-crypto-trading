"""
Binance Futures public REST API client.

Wraps the Binance USDT-margined Futures klines endpoint:
    https://fapi.binance.com/fapi/v1/klines

This client does NOT require API keys. It uses only public market-data
endpoints available without authentication.

Binance Futures kline field layout (index → field):
    0   open_time          ms timestamp (candle open)
    1   open               str price
    2   high               str price
    3   low                str price
    4   close              str price
    5   volume             str (base asset volume)
    6   close_time         ms timestamp (candle close)
    7   quote_volume       str
    8   trade_count        int
    9   taker_buy_base_vol str
   10   taker_buy_quote_vol str
   11   ignore             str (always "0")

Rate limits:
    Binance Futures: 2400 request weight/minute.
    Each /fapi/v1/klines call = 10 weight.
    At request_delay_ms=250ms: ~240 calls/min = 2400 weight/min (at limit).
    DEFAULT delay of 250ms keeps us safely within limits.

Design principles:
    - FAIL FAST: any HTTP error or malformed response raises DataIngestionError.
    - No silent fallbacks.
    - Bounded retries (max_retries) with explicit delay.
    - Every request is logged with URL, params, status, elapsed time.
    - Raw response is returned unmodified — no transformation at this layer.
"""

from __future__ import annotations

import time
from typing import Any

import requests

from crypto_research.core.exceptions import DataIngestionError
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BINANCE_FUTURES_BASE_URL = "https://fapi.binance.com"
KLINES_ENDPOINT = "/fapi/v1/klines"
KLINES_MAX_LIMIT = 1500  # Maximum candles per request on Futures API

# Binance Futures kline field indices
KLINE_OPEN_TIME = 0
KLINE_OPEN = 1
KLINE_HIGH = 2
KLINE_LOW = 3
KLINE_CLOSE = 4
KLINE_VOLUME = 5
KLINE_CLOSE_TIME = 6
KLINE_QUOTE_VOLUME = 7
KLINE_TRADE_COUNT = 8
KLINE_TAKER_BUY_BASE_VOL = 9
KLINE_TAKER_BUY_QUOTE_VOL = 10

# Timeframe string as accepted by Binance Futures API
BINANCE_INTERVAL_MAP: dict[str, str] = {
    "1m": "1m",
    "3m": "3m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "2h": "2h",
    "4h": "4h",
    "1d": "1d",
}


class BinanceFuturesClient:
    """
    Low-level HTTP client for the Binance USDT-margined Futures klines API.

    Responsibilities:
        - Fetch raw klines from Binance (public endpoint, no auth required).
        - Retry on transient failures (bounded, logged, with delay).
        - Raise DataIngestionError on permanent failures.
        - Never return partial or fabricated data.

    Usage:
        client = BinanceFuturesClient(request_delay_ms=250, max_retries=3)
        raw_klines = client.fetch_klines(
            symbol="BTCUSDT",
            interval="1m",
            start_ms=1704067200000,  # 2024-01-01 00:00 UTC in ms
            end_ms=1704153600000,    # 2024-01-02 00:00 UTC in ms
        )
    """

    def __init__(
        self,
        request_delay_ms: int = 250,
        max_retries: int = 3,
        retry_delay_s: int = 5,
        timeout_s: int = 30,
    ) -> None:
        """
        Args:
            request_delay_ms: Milliseconds to sleep between API calls.
            max_retries:      Maximum retry attempts for transient failures.
            retry_delay_s:    Seconds to wait between retries.
            timeout_s:        HTTP request timeout in seconds.
        """
        self._delay_s = request_delay_ms / 1000.0
        self._max_retries = max_retries
        self._retry_delay_s = retry_delay_s
        self._timeout_s = timeout_s
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})

    def fetch_klines(
        self,
        symbol: str,
        interval: str,
        start_ms: int,
        end_ms: int,
        limit: int = KLINES_MAX_LIMIT,
    ) -> list[list[Any]]:
        """
        Fetch raw klines from Binance Futures for the specified range.

        Args:
            symbol:   Trading pair, e.g. "BTCUSDT".
            interval: Binance interval string, e.g. "1m".
            start_ms: Start of range in milliseconds UTC (inclusive).
            end_ms:   End of range in milliseconds UTC (exclusive).
            limit:    Maximum candles per request (max 1500).

        Returns:
            List of raw kline lists as returned by Binance.
            Each inner list has 12 elements (see module-level field index map).
            Returns empty list if Binance returns no data for the range.

        Raises:
            DataIngestionError: On HTTP error, timeout, rate-limit, or
                malformed response — after exhausting all retries.
        """
        if interval not in BINANCE_INTERVAL_MAP:
            raise DataIngestionError(
                f"Unknown interval '{interval}'. "
                f"Valid values: {list(BINANCE_INTERVAL_MAP.keys())}"
            )

        params = {
            "symbol": symbol,
            "interval": BINANCE_INTERVAL_MAP[interval],
            "startTime": start_ms,
            "endTime": end_ms - 1,  # Binance end is inclusive; we make range exclusive
            "limit": min(limit, KLINES_MAX_LIMIT),
        }

        url = BINANCE_FUTURES_BASE_URL + KLINES_ENDPOINT
        last_exc: Exception | None = None

        for attempt in range(1, self._max_retries + 2):  # +2: initial + max_retries
            try:
                t0 = time.monotonic()
                response = self._session.get(url, params=params, timeout=self._timeout_s)
                elapsed_ms = (time.monotonic() - t0) * 1000

                logger.debug(
                    "Binance API request",
                    symbol=symbol,
                    interval=interval,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    status=response.status_code,
                    elapsed_ms=round(elapsed_ms, 1),
                    attempt=attempt,
                )

                # Handle rate-limit explicitly
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", self._retry_delay_s))
                    logger.warning(
                        "Binance rate limit hit",
                        symbol=symbol,
                        interval=interval,
                        retry_after_s=retry_after,
                        attempt=attempt,
                    )
                    if attempt <= self._max_retries:
                        time.sleep(retry_after)
                        continue
                    raise DataIngestionError(
                        f"Binance rate limit exceeded for {symbol}/{interval} "
                        f"after {self._max_retries} retries.\n"
                        f"Increase request_delay_ms in config or wait before retrying."
                    )

                # Handle IP ban
                if response.status_code == 418:
                    raise DataIngestionError(
                        f"Binance IP ban (HTTP 418) for {symbol}/{interval}. "
                        f"The API was called too aggressively. "
                        f"Wait before retrying and increase request_delay_ms."
                    )

                # Other HTTP errors — retry on 5xx, fail fast on 4xx
                if response.status_code >= 500:
                    error_text = response.text[:500]
                    logger.warning(
                        "Binance server error",
                        status=response.status_code,
                        body=error_text,
                        attempt=attempt,
                    )
                    if attempt <= self._max_retries:
                        time.sleep(self._retry_delay_s)
                        continue
                    raise DataIngestionError(
                        f"Binance server error {response.status_code} for "
                        f"{symbol}/{interval} after {self._max_retries} retries.\n"
                        f"Response: {error_text}"
                    )

                if response.status_code >= 400:
                    raise DataIngestionError(
                        f"Binance client error {response.status_code} for "
                        f"{symbol}/{interval}.\n"
                        f"Response: {response.text[:500]}\n"
                        f"This is a permanent error — check symbol and interval."
                    )

                # Parse JSON
                try:
                    data = response.json()
                except Exception as exc:
                    raise DataIngestionError(
                        f"Failed to parse Binance JSON response for {symbol}/{interval}.\n"
                        f"Raw response: {response.text[:200]}"
                    ) from exc

                if not isinstance(data, list):
                    raise DataIngestionError(
                        f"Unexpected Binance response type for {symbol}/{interval}. "
                        f"Expected list, got {type(data).__name__}.\n"
                        f"Response: {str(data)[:200]}"
                    )

                # Validate each kline has the expected field count
                for i, kline in enumerate(data):
                    if not isinstance(kline, list) or len(kline) < 11:
                        raise DataIngestionError(
                            f"Malformed kline at index {i} for {symbol}/{interval}. "
                            f"Expected list of ≥11 elements, got: {kline}"
                        )

                time.sleep(self._delay_s)
                return data

            except DataIngestionError:
                raise  # Never retry on DataIngestionError — it's already the final error
            except requests.exceptions.Timeout as exc:
                last_exc = exc
                logger.warning(
                    "Binance request timeout",
                    symbol=symbol,
                    interval=interval,
                    attempt=attempt,
                    timeout_s=self._timeout_s,
                )
            except requests.exceptions.ConnectionError as exc:
                last_exc = exc
                logger.warning(
                    "Binance connection error",
                    symbol=symbol,
                    interval=interval,
                    attempt=attempt,
                    error=str(exc),
                )

            if attempt <= self._max_retries:
                logger.info(
                    "Retrying request",
                    symbol=symbol,
                    interval=interval,
                    attempt=attempt,
                    next_attempt=attempt + 1,
                    delay_s=self._retry_delay_s,
                )
                time.sleep(self._retry_delay_s)

        raise DataIngestionError(
            f"Failed to fetch klines for {symbol}/{interval} "
            f"after {self._max_retries + 1} attempts.\n"
            f"Last error: {last_exc}"
        )

    def ping(self) -> bool:
        """
        Test connectivity to the Binance Futures API.

        Returns:
            True if the API is reachable.

        Raises:
            DataIngestionError: If the API cannot be reached.
        """
        try:
            response = self._session.get(
                BINANCE_FUTURES_BASE_URL + "/fapi/v1/ping",
                timeout=self._timeout_s,
            )
            if response.status_code == 200:
                return True
            raise DataIngestionError(
                f"Binance Futures API ping failed with HTTP {response.status_code}"
            )
        except requests.exceptions.RequestException as exc:
            raise DataIngestionError(
                f"Cannot reach Binance Futures API: {exc}\n"
                f"Check internet connectivity."
            ) from exc

    def get_server_time(self) -> int:
        """
        Return Binance server time in milliseconds UTC.

        Raises:
            DataIngestionError: If the request fails.
        """
        try:
            response = self._session.get(
                BINANCE_FUTURES_BASE_URL + "/fapi/v1/time",
                timeout=self._timeout_s,
            )
            response.raise_for_status()
            return response.json()["serverTime"]
        except Exception as exc:
            raise DataIngestionError(
                f"Failed to retrieve Binance server time: {exc}"
            ) from exc

    def get_exchange_info(self, symbol: str) -> dict:
        """
        Return exchange info for a specific symbol.

        Used to validate that a symbol exists and determine its
        actual listing date before downloading klines.

        Raises:
            DataIngestionError: If the symbol is not found or request fails.
        """
        try:
            response = self._session.get(
                BINANCE_FUTURES_BASE_URL + "/fapi/v1/exchangeInfo",
                timeout=self._timeout_s,
            )
            response.raise_for_status()
            info = response.json()
        except Exception as exc:
            raise DataIngestionError(
                f"Failed to retrieve Binance exchange info: {exc}"
            ) from exc

        symbols = {s["symbol"]: s for s in info.get("symbols", [])}
        if symbol not in symbols:
            raise DataIngestionError(
                f"Symbol '{symbol}' not found on Binance Futures.\n"
                f"Check the symbol spelling in config.yaml."
            )
        return symbols[symbol]
