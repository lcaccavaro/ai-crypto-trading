"""
Tests for BaseStrategy and StrategyRegistry.

Verifies:
- StrategyInfo validation
- BaseStrategy warm-up enforcement
- Registry register/get/list/filter/instantiate
- Registry duplicate registration → ValueError
- Registry unknown ID → KeyError
- StrategyInfo category validation
"""

import pytest
from datetime import datetime, timezone

from crypto_research.core.domain import Candle, Signal, SignalDirection, StrategyInfo, Timeframe
from crypto_research.strategies.base import BaseStrategy
from crypto_research.strategies.registry import StrategyRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_candle(close: float = 100.0, ts: datetime | None = None) -> Candle:
    ts = ts or datetime(2024, 1, 1, tzinfo=timezone.utc)
    return Candle(
        timestamp=ts,
        asset="BTCUSDT",
        timeframe=Timeframe.M15,
        open=close,
        high=close + 1.0,
        low=close - 1.0,
        close=close,
        volume=1000.0,
    )


def make_candles(n: int = 30, price: float = 100.0) -> list[Candle]:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    from datetime import timedelta
    return [
        make_candle(price + i * 0.1, base + timedelta(minutes=15 * i))
        for i in range(n)
    ]


def make_info(strategy_id: str = "TEST_001", category: str = "trend") -> StrategyInfo:
    return StrategyInfo(
        strategy_id=strategy_id,
        name="Test Strategy",
        version="1.0.0",
        category=category,
        hypothesis="Test hypothesis",
        description="Test description",
        warmup_period=10,
    )


class MinimalStrategy(BaseStrategy):
    """Minimal concrete implementation for testing BaseStrategy."""
    _info = make_info("MINIMAL_001")

    def __init__(self):
        super().__init__()
        self._signals_generated = 0

    @property
    def parameters(self) -> dict:
        return {}

    def _compute_signal(self, candles, timestamp):
        self._signals_generated += 1
        return None


# ---------------------------------------------------------------------------
# StrategyInfo validation
# ---------------------------------------------------------------------------

class TestStrategyInfo:
    def test_valid_creation(self):
        info = make_info()
        assert info.strategy_id == "TEST_001"
        assert info.warmup_period == 10

    def test_empty_strategy_id(self):
        with pytest.raises(ValueError, match="strategy_id"):
            StrategyInfo(
                strategy_id="", name="x", version="1.0.0", category="trend",
                hypothesis="h", description="d",
            )

    def test_empty_version(self):
        with pytest.raises(ValueError, match="version"):
            StrategyInfo(
                strategy_id="X", name="x", version="", category="trend",
                hypothesis="h", description="d",
            )

    def test_negative_warmup(self):
        with pytest.raises(ValueError, match="warmup_period"):
            StrategyInfo(
                strategy_id="X", name="x", version="1.0.0", category="trend",
                hypothesis="h", description="d", warmup_period=-1,
            )

    def test_invalid_category(self):
        with pytest.raises(ValueError, match="Invalid category"):
            StrategyInfo(
                strategy_id="X", name="x", version="1.0.0", category="invalid_cat",
                hypothesis="h", description="d",
            )

    def test_all_valid_categories(self):
        valid = [
            "trend", "momentum", "mean_reversion", "breakout",
            "volatility", "volume", "multi_indicator", "market_structure",
        ]
        for cat in valid:
            info = StrategyInfo(
                strategy_id="X", name="x", version="1.0.0", category=cat,
                hypothesis="h", description="d",
            )
            assert info.category == cat

    def test_is_frozen(self):
        info = make_info()
        with pytest.raises((AttributeError, TypeError)):
            info.strategy_id = "CHANGED"  # type: ignore


# ---------------------------------------------------------------------------
# BaseStrategy
# ---------------------------------------------------------------------------

class TestBaseStrategy:
    def test_warmup_blocks_signal(self):
        strat = MinimalStrategy()
        candles = make_candles(5)  # < warmup_period=10
        result = strat.generate_signal(candles, datetime.now(timezone.utc))
        assert result is None
        assert strat._signals_generated == 0  # _compute_signal not called

    def test_warmup_allows_signal(self):
        strat = MinimalStrategy()
        candles = make_candles(15)  # > warmup_period=10
        strat.generate_signal(candles, datetime.now(timezone.utc))
        assert strat._signals_generated == 1

    def test_name_equals_strategy_id(self):
        strat = MinimalStrategy()
        assert strat.name == "MINIMAL_001"

    def test_version(self):
        strat = MinimalStrategy()
        assert strat.version == "1.0.0"

    def test_repr(self):
        strat = MinimalStrategy()
        r = repr(strat)
        assert "MINIMAL_001" in r

    def test_missing_info_raises(self):
        class NoInfo(BaseStrategy):
            @property
            def parameters(self): return {}
            def _compute_signal(self, c, t): return None

        with pytest.raises(TypeError, match="_info"):
            NoInfo()

    def test_metadata_compatible(self):
        strat = MinimalStrategy()
        meta = strat.metadata
        assert meta.name == "MINIMAL_001"
        assert meta.version == "1.0.0"


# ---------------------------------------------------------------------------
# StrategyRegistry
# ---------------------------------------------------------------------------

class TestStrategyRegistry:
    def setup_method(self):
        """Use a fresh registry for each test — don't pollute global REGISTRY."""
        self.registry = StrategyRegistry()

    def _register_minimal(self, sid: str = "REG_TEST_001") -> type:
        info = make_info(sid)
        class RegStrategy(BaseStrategy):
            _info = info
            @property
            def parameters(self): return {}
            def _compute_signal(self, c, t): return None
        RegStrategy.__name__ = f"RegStrategy_{sid}"
        self.registry.register(RegStrategy)
        return RegStrategy

    def test_register_and_get(self):
        cls = self._register_minimal("REG_A_001")
        assert self.registry.get("REG_A_001") is cls

    def test_register_as_decorator(self):
        @self.registry.register
        class DecoratedStrategy(BaseStrategy):
            _info = make_info("DECO_001")
            @property
            def parameters(self): return {}
            def _compute_signal(self, c, t): return None

        assert "DECO_001" in self.registry

    def test_duplicate_registration_raises(self):
        self._register_minimal("DUPE_001")
        with pytest.raises(ValueError, match="already registered"):
            self._register_minimal("DUPE_001")

    def test_unknown_id_raises(self):
        with pytest.raises(KeyError):
            self.registry.get("NONEXISTENT_999")

    def test_list_sorted(self):
        self._register_minimal("ZZZ_001")
        self._register_minimal("AAA_001")
        ids = [info.strategy_id for info in self.registry.list()]
        assert ids == sorted(ids)

    def test_filter_by_category(self):
        self._register_minimal("TREND_REG_001")  # category=trend
        results = self.registry.filter_by_category("trend")
        assert any(i.strategy_id == "TREND_REG_001" for i in results)

    def test_instantiate_default_params(self):
        self._register_minimal("INST_001")
        instance = self.registry.instantiate("INST_001")
        assert isinstance(instance, BaseStrategy)

    def test_strategy_ids(self):
        self._register_minimal("SID_001")
        assert "SID_001" in self.registry.strategy_ids()

    def test_len(self):
        assert len(self.registry) == 0
        self._register_minimal("LEN_001")
        assert len(self.registry) == 1

    def test_contains(self):
        self._register_minimal("CONT_001")
        assert "CONT_001" in self.registry
        assert "MISSING" not in self.registry

    def test_non_strategy_raises(self):
        with pytest.raises(TypeError):
            self.registry.register(object)
