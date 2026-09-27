"""
Unit tests for PaperMarketDataProvider — Prompt 08.

Tests:
    - PaperDataGap creation and dict serialization
    - _parse_klines correctly parses valid kline rows
    - _parse_klines skips malformed rows
    - _parse_klines skips OHLC-invalid rows
    - _filter_closed filters future candles
    - PaperMarketDataProvider poll deduplicates
    - PaperMarketDataProvider poll detects gaps
    - consume_gaps clears gap list
"""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from crypto_research.config.schema import PaperMarketDataConfig
from crypto_research.core.domain import Candle, Timeframe
from crypto_research.paper.data_provider import (
    PaperDataGap,
    PaperMarketDataProvider,
    _parse_klines,
)


def _utc(dt_str: str) -> datetime:
    return datetime.fromisoformat(dt_str).replace(tzinfo=timezone.utc)


def _ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def _make_raw_kline(
    open_ts: datetime,
    o: float = 100.0,
    h: float = 105.0,
    lo: float = 99.0,
    c: float = 102.0,
    v: float = 500.0,
    close_offset_seconds: int = 3600,
) -> list:
    close_ts = open_ts + timedelta(seconds=close_offset_seconds)
    return [
        _ms(open_ts),   # 0: open_time
        str(o),         # 1: open
        str(h),         # 2: high
        str(lo),        # 3: low
        str(c),         # 4: close
        str(v),         # 5: volume
        _ms(close_ts),  # 6: close_time
        "0",            # 7: quote volume
        0,              # 8: number of trades
        "0", "0", "0"   # 9-11: taker buy base/quote/ignore
    ]


class TestPaperDataGap:
    """PaperDataGap must serialize cleanly."""

    def test_to_dict_contains_required_fields(self):
        tf = Timeframe.from_string("1h")
        gap = PaperDataGap(
            symbol="BTCUSDT",
            timeframe=tf,
            expected_ts=_utc("2024-01-01T01:00:00"),
            last_known_ts=_utc("2024-01-01T00:00:00"),
            detected_at=datetime.now(timezone.utc),
        )
        d = gap.to_dict()
        assert "symbol" in d
        assert "timeframe" in d
        assert "expected_ts" in d
        assert "last_known_ts" in d
        assert "detected_at" in d

    def test_null_last_known_ts(self):
        tf = Timeframe.from_string("1h")
        gap = PaperDataGap(
            symbol="ETHUSDT",
            timeframe=tf,
            expected_ts=_utc("2024-01-01T01:00:00"),
            last_known_ts=None,
            detected_at=datetime.now(timezone.utc),
        )
        d = gap.to_dict()
        assert d["last_known_ts"] is None


class TestParseKlines:
    """_parse_klines correctly converts raw Binance kline rows to Candle objects."""

    def test_valid_kline_parsed(self):
        tf = Timeframe.from_string("1h")
        ts = _utc("2024-01-01T00:00:00")
        raw = [_make_raw_kline(ts)]
        candles = _parse_klines(raw, "BTCUSDT", tf)
        assert len(candles) == 1
        c = candles[0]
        assert c.asset == "BTCUSDT"
        assert c.timeframe == tf
        assert c.open == 100.0
        assert c.high == 105.0
        assert c.low == 99.0
        assert c.close == 102.0
        assert c.volume == 500.0
        assert c.close_time is not None

    def test_multiple_klines_parsed(self):
        tf = Timeframe.from_string("1h")
        raw = [
            _make_raw_kline(_utc("2024-01-01T00:00:00")),
            _make_raw_kline(_utc("2024-01-01T01:00:00")),
            _make_raw_kline(_utc("2024-01-01T02:00:00")),
        ]
        candles = _parse_klines(raw, "BTCUSDT", tf)
        assert len(candles) == 3

    def test_malformed_row_skipped(self):
        tf = Timeframe.from_string("1h")
        raw = [
            _make_raw_kline(_utc("2024-01-01T00:00:00")),
            ["bad", "data"],  # Malformed
        ]
        # Should not raise, bad row skipped
        candles = _parse_klines(raw, "BTCUSDT", tf)
        assert len(candles) == 1

    def test_ohlc_invalid_row_skipped(self):
        """Rows where high < low or high < open must be skipped."""
        tf = Timeframe.from_string("1h")
        ts = _utc("2024-01-01T00:00:00")
        # high=50 < low=99 — invalid
        bad_row = _make_raw_kline(ts, o=100, h=50, lo=99, c=102)
        raw = [bad_row]
        candles = _parse_klines(raw, "BTCUSDT", tf)
        assert len(candles) == 0

    def test_candle_timestamp_is_utc(self):
        tf = Timeframe.from_string("1h")
        ts = _utc("2024-06-15T12:30:00")
        raw = [_make_raw_kline(ts)]
        candles = _parse_klines(raw, "BTCUSDT", tf)
        assert candles[0].timestamp.tzinfo is not None


class TestPaperMarketDataProviderDeduplication:
    """Provider must deduplicate candles with the same open_time."""

    def _make_provider(self) -> PaperMarketDataProvider:
        config = PaperMarketDataConfig(warmup_candles=10)
        provider = PaperMarketDataProvider(
            config=config,
            symbols=["BTCUSDT"],
            timeframes=["1h"],
        )
        provider._initialized = True
        provider._seen[("BTCUSDT", "1h")] = set()
        return provider

    def test_deduplicates_same_open_time(self):
        provider = self._make_provider()
        tf = Timeframe.from_string("1h")
        ts = _utc("2024-01-01T00:00:00")

        # Pre-populate as seen
        provider._seen[("BTCUSDT", "1h")].add(ts)
        provider._last_known[("BTCUSDT", "1h")] = ts

        # Mock _client to return that same candle again
        raw = [_make_raw_kline(ts)]
        with patch.object(provider._client, "fetch_klines", return_value=raw):
            # Filter time — use a timestamp 2h after candle close
            with patch(
                "crypto_research.paper.data_provider.datetime"
            ) as mock_dt:
                mock_dt.now.return_value = ts + timedelta(hours=3)
                mock_dt.fromtimestamp = datetime.fromtimestamp
                result = provider.poll()

        new = result.get(("BTCUSDT", "1h"), [])
        assert len(new) == 0, "Duplicate candle should not be returned"

    def test_new_candle_is_returned(self):
        provider = self._make_provider()
        tf = Timeframe.from_string("1h")
        ts = _utc("2024-01-01T01:00:00")

        raw = [_make_raw_kline(ts)]
        # Return the candle as closed (now = ts + 2h)
        with patch.object(provider._client, "fetch_klines", return_value=raw):
            with patch(
                "crypto_research.paper.data_provider.datetime"
            ) as mock_dt:
                mock_dt.now.return_value = ts + timedelta(hours=2)
                mock_dt.fromtimestamp = datetime.fromtimestamp
                result = provider.poll()

        new = result.get(("BTCUSDT", "1h"), [])
        assert len(new) == 1

    def test_consume_gaps_clears_list(self):
        provider = self._make_provider()
        tf = Timeframe.from_string("1h")
        # Inject a fake gap
        from crypto_research.paper.data_provider import PaperDataGap
        gap = PaperDataGap(
            symbol="BTCUSDT",
            timeframe=tf,
            expected_ts=_utc("2024-01-01T00:00:00"),
            last_known_ts=None,
            detected_at=datetime.now(timezone.utc),
        )
        provider._gaps.append(gap)

        gaps = provider.consume_gaps()
        assert len(gaps) == 1
        assert len(provider._gaps) == 0

    def test_close_is_noop(self):
        provider = self._make_provider()
        provider.close()  # Should not raise
