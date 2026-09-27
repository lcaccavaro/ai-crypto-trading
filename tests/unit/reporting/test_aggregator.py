"""Unit tests for reporting aggregator."""
from datetime import datetime, timezone
import pytest

from crypto_research.reporting.models import TradeDiaryRecord
from crypto_research.reporting.aggregator import ReportAggregator
from crypto_research.core.domain import PortfolioState

def test_daily_aggregation():
    ps = [
        PortfolioState(datetime(2026, 1, 1, 0, tzinfo=timezone.utc), 10000.0, 10000.0, 10000.0, 10000.0, 0, 0, 0, 0, 0, 0, 0, 0, 10000.0, "OPEN", {}, {}, {})
    ]
    agg = ReportAggregator(ps)
    
    t1 = TradeDiaryRecord(
        run_id="r1", trade_id="t1", strategy_id="s1", strategy_version="1", symbol="BTC",
        market_type="futures", timeframe="15m", side="LONG",
        signal_timestamp=datetime(2026, 1, 1, 10, tzinfo=timezone.utc),
        entry_timestamp=datetime(2026, 1, 1, 10, tzinfo=timezone.utc),
        entry_price=100.0, initial_stop_price=90.0, target_price=120.0,
        final_exit_timestamp=datetime(2026, 1, 1, 11, tzinfo=timezone.utc),
        final_exit_price=120.0, position_size=1.0, notional_value=100.0,
        risk_amount=10.0, risk_pct=1.0, configured_RR=2.0, realized_R=2.0,
        gross_pnl=20.0, fees=0.5, spread_cost=0, slippage_cost=0, total_cost=0.5,
        net_pnl=19.5, net_return_pct=0.195, holding_duration_seconds=3600
    )
    
    t2 = TradeDiaryRecord(
        run_id="r1", trade_id="t2", strategy_id="s1", strategy_version="1", symbol="ETH",
        market_type="futures", timeframe="15m", side="SHORT",
        signal_timestamp=datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
        entry_timestamp=datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
        entry_price=100.0, initial_stop_price=110.0, target_price=80.0,
        final_exit_timestamp=datetime(2026, 1, 1, 13, tzinfo=timezone.utc),
        final_exit_price=110.0, position_size=1.0, notional_value=100.0,
        risk_amount=10.0, risk_pct=1.0, configured_RR=2.0, realized_R=-1.0,
        gross_pnl=-10.0, fees=0.5, spread_cost=0, slippage_cost=0, total_cost=0.5,
        net_pnl=-10.5, net_return_pct=-0.105, holding_duration_seconds=3600
    )
    
    reports = agg.aggregate_daily([t1, t2])
    
    assert len(reports) == 1
    r = reports[0]
    assert r.date == "2026-01-01"
    assert r.executed_trades == 2
    assert r.wins == 1
    assert r.losses == 1
    assert r.net_pnl == 9.0
    assert r.total_costs == 1.0
    assert r.average_R == 0.5
    assert r.asset_count == 2
