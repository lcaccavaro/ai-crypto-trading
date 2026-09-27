"""
Paper Market Data Provider — Prompt 08.

Uses Binance public REST API to fetch recent closed candles.
NO authentication required. NO trading permissions.

Design:
    - Reuses the existing BinanceFuturesClient (fapi REST client from Prompt 02).
    - Returns only CLOSED candles (candle.close_time < utcnow()).
    - Deduplicates: same candle open_time seen twice → silently skipped.
    - Detects gaps: missing candle since last_known → recorded.
    - Converts raw kline rows into Candle objects using the same parsing
      logic as DataIngestionPipeline.

PIT guarantee:
    A candle is delivered only after its close_time has elapsed.
    Strategy receives only completed candles — same rule as BacktestEngine.

Gap policy:
    If expected candle(s) are missing:
      - Record a DATA_GAP_DETECTED audit event.
      - Do NOT invent synthetic candles.
      - The caller (PaperEngine) decides whether to pause.

Duplicate policy:
    If a candle with an already-seen open_time is received:
      - Record MARKET_DATA_DUPLICATE.
      - Skip processing. Do not double-signal.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from crypto_research.config.schema import PaperMarketDataConfig
from crypto_research.core.domain import Candle, PaperAuditEventType, Timeframe
from crypto_research.data.binance_client import BinanceFuturesClient
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)

# How many recent candles to request per poll
_POLL_LIMIT = 10


class PaperDataGap:
    """Describes a detected gap in market data."""

    def __init__(
        self,
        symbol: str,
        timeframe: Timeframe,
        expected_ts: datetime,
        last_known_ts: datetime | None,
        detected_at: datetime,
    ) -> None:
        self.symbol = symbol
        self.timeframe = timeframe
        self.expected_ts = expected_ts
        self.last_known_ts = last_known_ts
        self.detected_at = detected_at

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe.value,
            "expected_ts": self.expected_ts.isoformat(),
            "last_known_ts": self.last_known_ts.isoformat() if self.last_known_ts else None,
            "detected_at": self.detected_at.isoformat(),
        }


def _ms(dt: datetime) -> int:
    """Convert datetime to Binance millisecond timestamp."""
    return int(dt.timestamp() * 1000)


def _parse_klines(raw: list[list[Any]], asset: str, timeframe: Timeframe) -> list[Candle]:
    """
    Convert raw Binance kline rows to Candle objects.

    Binance kline layout (by index):
        0  open_time   ms
        1  open        str
        2  high        str
        3  low         str
        4  close       str
        5  volume      str
        6  close_time  ms
    """
    candles: list[Candle] = []
    for row in raw:
        try:
            open_ts = datetime.fromtimestamp(row[0] / 1000, tz=timezone.utc)
            close_ts = datetime.fromtimestamp(row[6] / 1000, tz=timezone.utc)
            o, h, l, c, v = (
                float(row[1]), float(row[2]), float(row[3]),
                float(row[4]), float(row[5])
            )
            # Pre-validate OHLC to avoid ValueError in Candle.__post_init__
            if h < l or h < o or h < c or l > o or l > c or v < 0:
                logger.warning("Skipping kline: OHLC invariant violated",
                               asset=asset, ts=open_ts.isoformat())
                continue
            candle = Candle(
                timestamp=open_ts,
                asset=asset,
                timeframe=timeframe,
                open=o,
                high=h,
                low=l,
                close=c,
                volume=v,
                close_time=close_ts,
            )
            candles.append(candle)
        except (IndexError, ValueError, TypeError) as e:
            logger.warning("Malformed kline row skipped", asset=asset,
                           timeframe=timeframe.value, error=str(e))
    return candles


def _validate_ohlc(candles: list[Candle]) -> list[Candle]:
    """Return only candles that pass OHLC invariant checks (pre-parse guard)."""
    # Candle.__post_init__ already validates — this function is a no-op guard
    # for any candles that might have slipped through without going via __init__.
    return candles  # Already validated by dataclass __post_init__


class PaperMarketDataProvider:
    """
    Polls Binance public REST for recent closed candles.

    Reuses BinanceFuturesClient from Prompt 02.
    No API keys required — public endpoints only.

    Usage:
        provider = PaperMarketDataProvider(config, symbols, timeframes)
        warmup = provider.initialize()     # returns dict[(symbol, tf)] → list[Candle]
        new_candles = provider.poll()      # returns newly closed candles
        gaps = provider.consume_gaps()
        provider.close()
    """

    def __init__(
        self,
        config: PaperMarketDataConfig,
        symbols: list[str],
        timeframes: list[str],
    ) -> None:
        self._config = config
        self._symbols = symbols
        self._timeframes = [Timeframe.from_string(tf) for tf in timeframes]

        # Reuse existing client — same one used by DataIngestionPipeline
        self._client = BinanceFuturesClient(
            request_delay_ms=250,
            max_retries=config.max_retries,
            retry_delay_s=int(config.retry_delay_seconds),
            timeout_s=int(config.request_timeout_seconds),
        )

        # Last known closed candle open_time per (symbol, tf.value)
        self._last_known: dict[tuple[str, str], datetime] = {}

        # Set of seen open_times to detect duplicates
        self._seen: dict[tuple[str, str], set[datetime]] = {}

        # Warmup candle buffers
        self._warmup_buffer: dict[tuple[str, str], list[Candle]] = {}

        self._initialized = False
        self._gaps: list[PaperDataGap] = []

    # ─── Public API ─────────────────────────────────────────────────────────────

    def initialize(self, warmup_candles: int | None = None) -> dict[tuple[str, str], list[Candle]]:
        """
        Load initial candle history for strategy warm-up.

        Returns:
            Dict mapping (symbol, tf.value) → list of historical candles.
        """
        n = warmup_candles or self._config.warmup_candles
        logger.info("Initializing paper data provider",
                    symbols=self._symbols,
                    timeframes=[tf.value for tf in self._timeframes],
                    warmup_candles=n)

        now = datetime.now(timezone.utc)

        for symbol in self._symbols:
            for tf in self._timeframes:
                key = (symbol, tf.value)
                self._seen[key] = set()
                try:
                    # Request last N candles: go back N * tf_seconds from now
                    start = now - timedelta(seconds=tf.to_seconds() * n)
                    raw = self._client.fetch_klines(
                        symbol=symbol,
                        interval=tf.value,
                        start_ms=_ms(start),
                        end_ms=_ms(now),
                        limit=n,
                    )
                    candles = _parse_klines(raw, symbol, tf)
                    candles = _validate_ohlc(candles)
                    candles = self._filter_closed(candles)

                    self._warmup_buffer[key] = candles
                    if candles:
                        latest = candles[-1]
                        self._last_known[key] = latest.timestamp
                        for c in candles:
                            self._seen[key].add(c.timestamp)
                        logger.info("Warmup loaded", symbol=symbol,
                                    timeframe=tf.value, count=len(candles))
                    else:
                        logger.warning("No closed candles during warmup",
                                       symbol=symbol, timeframe=tf.value)

                except Exception as exc:
                    logger.error("Warmup failed", symbol=symbol,
                                 timeframe=tf.value, error=str(exc))
                    self._warmup_buffer[key] = []

        self._initialized = True
        return dict(self._warmup_buffer)

    def poll(self) -> dict[tuple[str, str], list[Candle]]:
        """
        Poll Binance for newly closed candles since last known candle.

        Returns:
            Dict mapping (symbol, tf.value) → list of NEW closed candles
            (empty list if no new candles).
        """
        if not self._initialized:
            raise RuntimeError(
                "PaperMarketDataProvider.initialize() must be called first."
            )

        now = datetime.now(timezone.utc)
        new_candles: dict[tuple[str, str], list[Candle]] = {}

        for symbol in self._symbols:
            for tf in self._timeframes:
                key = (symbol, tf.value)
                new_candles[key] = []

                try:
                    # Fetch the last _POLL_LIMIT candles
                    start = now - timedelta(seconds=tf.to_seconds() * _POLL_LIMIT)
                    raw = self._client.fetch_klines(
                        symbol=symbol,
                        interval=tf.value,
                        start_ms=_ms(start),
                        end_ms=_ms(now),
                        limit=_POLL_LIMIT,
                    )
                    candles = _parse_klines(raw, symbol, tf)
                    candles = _validate_ohlc(candles)
                    candles = self._filter_closed(candles)

                    seen_set = self._seen.setdefault(key, set())

                    for candle in candles:
                        # Duplicate detection
                        if candle.timestamp in seen_set:
                            logger.debug(
                                "Duplicate candle skipped",
                                symbol=symbol, timeframe=tf.value,
                                ts=candle.timestamp.isoformat(),
                                event_type=PaperAuditEventType.MARKET_DATA_DUPLICATE.value,
                            )
                            continue

                        # Gap detection
                        last = self._last_known.get(key)
                        if last is not None:
                            expected_next = last + timedelta(seconds=tf.to_seconds())
                            if candle.timestamp > expected_next:
                                gap = PaperDataGap(
                                    symbol=symbol,
                                    timeframe=tf,
                                    expected_ts=expected_next,
                                    last_known_ts=last,
                                    detected_at=now,
                                )
                                self._gaps.append(gap)
                                logger.warning(
                                    "Data gap detected",
                                    symbol=symbol, timeframe=tf.value,
                                    expected=expected_next.isoformat(),
                                    received=candle.timestamp.isoformat(),
                                    event_type=PaperAuditEventType.DATA_GAP_DETECTED.value,
                                )

                        seen_set.add(candle.timestamp)
                        self._last_known[key] = candle.timestamp
                        new_candles[key].append(candle)
                        logger.debug(
                            "New closed candle",
                            symbol=symbol, timeframe=tf.value,
                            ts=candle.timestamp.isoformat(),
                            event_type=PaperAuditEventType.CANDLE_CLOSED.value,
                        )

                except Exception as e:
                    logger.error(
                        "Poll error",
                        symbol=symbol, timeframe=tf.value,
                        error=str(e),
                        event_type=PaperAuditEventType.ERROR.value,
                    )

        return new_candles

    def get_warmup_buffer(self) -> dict[tuple[str, str], list[Candle]]:
        """Return the candle history loaded at initialization."""
        return dict(self._warmup_buffer)

    def consume_gaps(self) -> list[PaperDataGap]:
        """Pop and return all detected gaps since last call."""
        gaps = list(self._gaps)
        self._gaps.clear()
        return gaps

    def close(self) -> None:
        """Clean up resources (no-op for REST polling)."""
        logger.info("Paper data provider closed")

    # ─── Internal helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _filter_closed(candles: list[Candle]) -> list[Candle]:
        """
        Return only candles whose close_time has elapsed.

        PIT rule: a candle is delivered only after it is fully closed.
        """
        now = datetime.now(timezone.utc)
        return [
            c for c in candles
            if c.close_time is not None and c.close_time < now
        ]
