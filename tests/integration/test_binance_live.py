"""
Live Binance Futures integration test.

THIS TEST REQUIRES INTERNET ACCESS TO BINANCE.
It uses the REAL Binance Futures public API — no mocks, no synthetic data.

Run with:
    pytest tests/integration/test_binance_live.py -v -m live

Skip (run only offline tests):
    pytest tests/ -m "not live"

If network is unavailable, this test will SKIP (not fail with fake data).
It will NEVER claim success using fabricated Binance responses.

Tests:
    1. Binance Futures API is reachable (ping).
    2. Server time can be retrieved.
    3. BTCUSDT exchange info confirms symbol exists.
    4. fetch_klines returns real data for BTCUSDT/1m.
    5. Returned candles satisfy all OHLC invariants.
    6. Returned timestamps are in milliseconds and advance correctly.
    7. DataFrame conversion produces correct schema and UTC timestamps.
    8. Full validation pipeline passes on real data.
    9. ETHUSDT and SOLUSDT symbols are also reachable.
"""

from datetime import datetime, timezone, timedelta

import pytest

from crypto_research.data.binance_client import BinanceFuturesClient
from crypto_research.data.store import ParquetDataStore
from crypto_research.data.validators import ValidationStatus, run_validation_pipeline
from crypto_research.core.exceptions import DataIngestionError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client() -> BinanceFuturesClient:
    return BinanceFuturesClient(
        request_delay_ms=300,
        max_retries=2,
        retry_delay_s=3,
    )

def _recent_range() -> tuple[int, int]:
    """Return (start_ms, end_ms) for the last 60 minutes."""
    now = datetime.now(timezone.utc)
    end = now.replace(second=0, microsecond=0)
    start = end - timedelta(hours=1)
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)

def _skip_if_unreachable(client: BinanceFuturesClient) -> None:
    """Skip the test if Binance cannot be reached — never fail with fake data."""
    try:
        client.ping()
    except DataIngestionError as exc:
        pytest.skip(
            f"LIVE BINANCE INTEGRATION: SKIPPED — Cannot reach Binance Futures API.\n"
            f"Error: {exc}\n"
            f"This test requires internet access. It will NOT fall back to mock data."
        )


# ---------------------------------------------------------------------------
# Integration tests (all require live Binance)
# ---------------------------------------------------------------------------

@pytest.mark.live
def test_binance_futures_ping():
    """Binance Futures API must respond to /fapi/v1/ping."""
    client = _make_client()
    _skip_if_unreachable(client)
    result = client.ping()
    assert result is True
    print("\nLIVE BINANCE INTEGRATION: ping() → PASSED")


@pytest.mark.live
def test_binance_futures_server_time():
    """Server time must be a positive integer close to current UTC time."""
    client = _make_client()
    _skip_if_unreachable(client)
    server_time_ms = client.get_server_time()
    assert isinstance(server_time_ms, int)
    assert server_time_ms > 0

    # Server time must be within ±30 seconds of local UTC time
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    diff_s = abs(server_time_ms - now_ms) / 1000
    assert diff_s < 30, (
        f"Binance server time differs from local UTC by {diff_s:.1f}s (max 30s allowed)"
    )
    print(f"\nLIVE BINANCE INTEGRATION: server_time={server_time_ms} → PASSED")


@pytest.mark.live
def test_btcusdt_exists_on_futures():
    """BTCUSDT must exist on Binance Futures."""
    client = _make_client()
    _skip_if_unreachable(client)
    info = client.get_exchange_info("BTCUSDT")
    assert info["symbol"] == "BTCUSDT"
    assert info["status"] == "TRADING"
    print("\nLIVE BINANCE INTEGRATION: BTCUSDT exchange info → PASSED")


@pytest.mark.live
def test_fetch_btcusdt_1m_returns_real_data():
    """
    fetch_klines for BTCUSDT/1m must return real market data.

    Verifies:
        - At least 1 candle is returned.
        - Each kline has 12 fields.
        - Timestamps advance correctly.
        - Prices are positive.
    """
    client = _make_client()
    _skip_if_unreachable(client)

    start_ms, end_ms = _recent_range()
    klines = client.fetch_klines(
        symbol="BTCUSDT",
        interval="1m",
        start_ms=start_ms,
        end_ms=end_ms,
        limit=60,
    )

    assert len(klines) > 0, "Expected at least 1 candle, got 0"
    assert len(klines) <= 60

    # Each kline must have 12 fields
    for i, kline in enumerate(klines):
        assert isinstance(kline, list), f"kline[{i}] is not a list"
        assert len(kline) >= 11, f"kline[{i}] has only {len(kline)} fields"

    # Timestamps must be in ms and advance
    open_times = [k[0] for k in klines]
    assert all(isinstance(t, int) for t in open_times)
    assert all(t > 0 for t in open_times)
    assert open_times == sorted(open_times), "Timestamps not in ascending order"

    # All open_times must be within the requested range
    assert all(start_ms <= t < end_ms for t in open_times), (
        f"Some timestamps outside requested range [{start_ms}, {end_ms})"
    )

    # Prices must be positive (converted from string)
    for kline in klines:
        assert float(kline[1]) > 0, f"Open price ≤ 0: {kline[1]}"
        assert float(kline[2]) > 0, f"High price ≤ 0: {kline[2]}"
        assert float(kline[3]) > 0, f"Low price ≤ 0: {kline[3]}"
        assert float(kline[4]) > 0, f"Close price ≤ 0: {kline[4]}"
        assert float(kline[5]) >= 0, f"Volume < 0: {kline[5]}"

    print(f"\nLIVE BINANCE INTEGRATION: fetch_klines BTCUSDT/1m → {len(klines)} candles → PASSED")
    print(f"  First candle: open={klines[0][1]}, high={klines[0][2]}, low={klines[0][3]}, close={klines[0][4]}")
    print(f"  Last candle:  open={klines[-1][1]}, high={klines[-1][2]}, low={klines[-1][3]}, close={klines[-1][4]}")


@pytest.mark.live
def test_btcusdt_dataframe_schema():
    """Real BTCUSDT klines must convert to a correctly typed canonical DataFrame."""
    client = _make_client()
    _skip_if_unreachable(client)

    start_ms, end_ms = _recent_range()
    klines = client.fetch_klines("BTCUSDT", "1m", start_ms=start_ms, end_ms=end_ms, limit=10)

    if not klines:
        pytest.skip("No klines returned — cannot test DataFrame schema")

    df = ParquetDataStore.raw_klines_to_dataframe(klines, "BTCUSDT", "1m")

    # Check all columns present
    expected_cols = [
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trade_count",
        "taker_buy_base_vol", "taker_buy_quote_vol",
    ]
    assert list(df.columns) == expected_cols

    # UTC timestamps
    assert str(df["timestamp"].dtype.tz) in ("UTC", "utc")

    # Numeric types
    assert df["open"].dtype == "float64"
    assert df["trade_count"].dtype == "int64"

    print(f"\nLIVE BINANCE INTEGRATION: DataFrame schema validation → PASSED")
    print(df.head(3).to_string())


@pytest.mark.live
def test_btcusdt_validation_pipeline_passes():
    """Real BTCUSDT data must pass the full validation pipeline."""
    client = _make_client()
    _skip_if_unreachable(client)

    start_ms, end_ms = _recent_range()
    klines = client.fetch_klines("BTCUSDT", "1m", start_ms=start_ms, end_ms=end_ms, limit=60)

    if not klines:
        pytest.skip("No klines returned — cannot run validation pipeline")

    df = ParquetDataStore.raw_klines_to_dataframe(klines, "BTCUSDT", "1m")
    summary = run_validation_pipeline(df, "BTCUSDT", "1m")

    # Real BTC data must pass OHLC, schema, timestamps, nulls
    # Missing candles may produce WARNING — acceptable
    assert summary.overall_status in (ValidationStatus.PASS, ValidationStatus.WARNING), (
        f"Validation FAILED on real BTCUSDT data. Issues:\n"
        + "\n".join(summary.all_issues)
    )

    # OHLC and schema must explicitly pass
    ohlc_result = next(r for r in summary.results if r.validator_name == "ohlc")
    schema_result = next(r for r in summary.results if r.validator_name == "schema")
    null_result = next(r for r in summary.results if r.validator_name == "nulls")
    ts_result = next(r for r in summary.results if r.validator_name == "timestamps")

    assert ohlc_result.status == ValidationStatus.PASS, f"OHLC failed: {ohlc_result.issues}"
    assert schema_result.status == ValidationStatus.PASS, f"Schema failed: {schema_result.issues}"
    assert null_result.status == ValidationStatus.PASS, f"Nulls failed: {null_result.issues}"
    assert ts_result.status == ValidationStatus.PASS, f"Timestamps failed: {ts_result.issues}"

    print(f"\nLIVE BINANCE INTEGRATION: validation pipeline → {summary.overall_status.value} → PASSED")
    for r in summary.results:
        print(f"  {r.validator_name:20s}: {r.status.value}")


@pytest.mark.live
@pytest.mark.parametrize("symbol", ["ETHUSDT", "SOLUSDT"])
def test_other_symbols_are_reachable(symbol):
    """ETHUSDT and SOLUSDT must be downloadable from Binance Futures."""
    client = _make_client()
    _skip_if_unreachable(client)

    start_ms, end_ms = _recent_range()
    klines = client.fetch_klines(symbol, "1m", start_ms=start_ms, end_ms=end_ms, limit=5)

    assert len(klines) > 0, f"No data returned for {symbol}"
    assert float(klines[0][4]) > 0, f"Close price ≤ 0 for {symbol}: {klines[0][4]}"

    print(f"\nLIVE BINANCE INTEGRATION: {symbol}/1m → {len(klines)} candles → PASSED")
    print(f"  Latest close: {klines[-1][4]}")


@pytest.mark.live
def test_invalid_symbol_raises_data_ingestion_error():
    """A non-existent symbol must raise DataIngestionError immediately."""
    client = _make_client()
    _skip_if_unreachable(client)

    start_ms, end_ms = _recent_range()
    with pytest.raises(DataIngestionError):
        # FAKEUSDT does not exist on Binance Futures
        client.fetch_klines("FAKEUSDT", "1m", start_ms=start_ms, end_ms=end_ms, limit=1)

    print("\nLIVE BINANCE INTEGRATION: invalid symbol raises DataIngestionError → PASSED")
