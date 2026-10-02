"""
StrategyAdapter — adapta estratégias P04 (BaseStrategy) para o engine P03.

O BacktestEngine chama:
    strategy.on_candle(close_price, symbol, timeframe, timestamp) -> dict | None

As estratégias P04 expõem:
    strategy.generate_signal(candles: list[Candle], timestamp) -> Signal | None

Este adaptador faz a ponte mantendo um buffer de candles e calculando
stop/target com base em % do preço (pois o engine só passa close_price,
não temos acesso ao OHLC completo para ATR aqui).
"""
from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import Deque

from crypto_research.core.domain import Candle, SignalDirection, Timeframe


class StrategyAdapter:
    """
    Adapta um BaseStrategy (P04) para a interface on_candle() do BacktestEngine (P03).

    Stop calculado como percentual do preço de entrada (stop_pct).
    Target calculado como stop_distance * rr_ratio.

    Uso:
        base = REGISTRY.instantiate("RSI_MOMENTUM_001")
        strategy = StrategyAdapter(base, rr_ratio=3.0, stop_pct=1.0)
        engine.run(strategy, run_id="RUN_001")
    """

    def __init__(
        self,
        strategy,
        rr_ratio: float = 3.0,
        stop_pct: float = 1.0,       # stop = stop_pct% abaixo do preço de entrada
        buffer_size: int = 500,
    ) -> None:
        self._strategy   = strategy
        self._rr         = rr_ratio
        self._stop_pct   = stop_pct / 100.0
        self._buffers: dict[str, deque] = {}
        self._buffer_size = buffer_size

    @property
    def name(self) -> str:
        return self._strategy.name

    @property
    def version(self) -> str:
        return self._strategy.version

    @property
    def parameters(self) -> dict:
        return self._strategy.parameters

    def on_candle(
        self,
        close_price: float,
        symbol: str,
        timeframe: str,
        timestamp: datetime,
    ) -> dict | None:
        """
        Interface compatível com BacktestEngine.run().
        Mantém buffer de Candle, chama generate_signal, converte para dict.
        """
        key = f"{symbol}_{timeframe}"
        if key not in self._buffers:
            self._buffers[key] = deque(maxlen=self._buffer_size)

        buf = self._buffers[key]

        # Cria Candle com open=high=low=close (engine só fornece close_price aqui)
        candle = Candle(
            timestamp=timestamp,
            asset=symbol,
            timeframe=Timeframe(timeframe),
            open=close_price,
            high=close_price,
            low=close_price,
            close=close_price,
            volume=1.0,
        )
        buf.append(candle)

        candles_list = list(buf)
        signal = self._strategy.generate_signal(candles_list, timestamp)

        if signal is None:
            return None

        if signal.direction != SignalDirection.LONG:
            return None  # Engine P03 suporta apenas LONG

        # Stop/target via % do preço (robusto quando não temos OHLC real)
        stop_distance = close_price * self._stop_pct
        stop_price    = close_price - stop_distance
        target_price  = close_price + stop_distance * self._rr

        return {
            "direction":     signal.direction,
            "stop_price":    stop_price,
            "target_price":  target_price,
            "strength":      signal.strength,
            "strategy_name": signal.strategy_name,
        }

    def reset(self) -> None:
        self._buffers.clear()
        self._strategy.reset()
