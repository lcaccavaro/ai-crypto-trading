"""
Cost model for the backtest engine.

All execution costs are computed by pure, stateless functions here.
No magic constants are embedded in the engine — every cost assumption
is explicit and driven by configuration.

Cost calculation (documented to avoid double-counting):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For a BUY order at requested_price P:

    spread_component  = P × (spread_bps / 10000) / 2
        → Half the spread is paid by the buyer (crossing the ask side).
          This is a simplification: we assume the trader is a price-taker.

    slippage_component = P × (slippage_bps / 10000)
        → Market impact: execution price is worse than the mid-price.
          Applies in the direction adverse to the trader.

    execution_price (BUY)  = P + spread_component + slippage_component
    execution_price (SELL) = P - spread_component - slippage_component

    fee = execution_price × quantity × fee_rate

    spread_cost  = spread_component × quantity   (informational)
    slippage_cost = slippage_component × quantity (informational)

These three costs (fee, spread_cost, slippage_cost) are tracked separately
so that research can evaluate each component's contribution to net PnL.

IMPORTANT: Do NOT add slippage_component and spread_component separately
to get the execution price — use calculate_execution_price() which combines
them correctly and consistently.
"""

from __future__ import annotations

from dataclasses import dataclass

from crypto_research.core.domain import OrderSide


@dataclass(frozen=True)
class CostModel:
    """
    Immutable cost model configuration.

    Instantiated once per backtest run from the configuration.

    Attributes:
        slippage_bps:    Slippage in basis points (applied per side).
        spread_bps:      Full spread in basis points. Half-spread paid per trade.
        taker_fee_rate:  Fee rate for market (taker) orders (e.g. 0.0005 = 0.05%).
        maker_fee_rate:  Fee rate for limit (maker) orders (e.g. 0.0002 = 0.02%).
    """

    slippage_bps: float
    spread_bps: float
    taker_fee_rate: float
    maker_fee_rate: float

    def calculate_execution_price(self, mid_price: float, side: OrderSide) -> float:
        """
        Compute the actual fill price including slippage and half-spread.

        For BUY orders:  execution_price > mid_price (costs adversely)
        For SELL orders: execution_price < mid_price (costs adversely)

        Args:
            mid_price: The reference price (e.g. candle open, close, or stop level).
            side:      Order side (BUY or SELL).

        Returns:
            Adjusted execution price.
        """
        half_spread = mid_price * (self.spread_bps / 10_000) / 2
        slippage = mid_price * (self.slippage_bps / 10_000)
        cost = half_spread + slippage

        if side == OrderSide.BUY:
            return mid_price + cost
        else:
            return mid_price - cost

    def calculate_slippage_amount(self, mid_price: float, quantity: float) -> float:
        """
        Compute the slippage cost in quote asset terms.

        Args:
            mid_price: Reference price.
            quantity:  Position size in base asset.

        Returns:
            Slippage cost in quote asset (always non-negative).
        """
        slippage_per_unit = mid_price * (self.slippage_bps / 10_000)
        return slippage_per_unit * quantity

    def calculate_spread_cost(self, mid_price: float, quantity: float) -> float:
        """
        Compute the half-spread cost in quote asset terms.

        Args:
            mid_price: Reference price.
            quantity:  Position size in base asset.

        Returns:
            Half-spread cost in quote asset (always non-negative).
        """
        half_spread_per_unit = mid_price * (self.spread_bps / 10_000) / 2
        return half_spread_per_unit * quantity

    def calculate_fee(
        self, execution_price: float, quantity: float, is_maker: bool = False
    ) -> float:
        """
        Compute the trading fee in quote asset terms.

        Args:
            execution_price: Final execution price (after slippage/spread).
            quantity:        Position size in base asset.
            is_maker:        True for limit orders (maker), False for market (taker).

        Returns:
            Fee in quote asset (always non-negative).
        """
        rate = self.maker_fee_rate if is_maker else self.taker_fee_rate
        return execution_price * quantity * rate

    def compute_entry_costs(
        self, mid_price: float, quantity: float, side: OrderSide, is_maker: bool = False
    ) -> tuple[float, float, float, float]:
        """
        Compute all costs for an entry fill.

        Returns:
            Tuple of (execution_price, fee, slippage_cost, spread_cost).

        All returned values are non-negative (absolute amounts).
        execution_price is directional (higher for buys, lower for sells).
        """
        execution_price = self.calculate_execution_price(mid_price, side)
        slippage_cost = self.calculate_slippage_amount(mid_price, quantity)
        spread_cost = self.calculate_spread_cost(mid_price, quantity)
        fee = self.calculate_fee(execution_price, quantity, is_maker=is_maker)
        return execution_price, fee, slippage_cost, spread_cost

    @classmethod
    def from_config(cls, execution_cfg, costs_cfg) -> "CostModel":
        """
        Construct a CostModel from the project configuration objects.

        Args:
            execution_cfg: ExecutionConfig (for slippage_bps, spread_bps).
            costs_cfg:     CostsConfig (for fee rates).

        Returns:
            Configured CostModel instance.
        """
        return cls(
            slippage_bps=execution_cfg.slippage_bps,
            spread_bps=execution_cfg.spread_bps,
            taker_fee_rate=costs_cfg.taker_fee_rate,
            maker_fee_rate=costs_cfg.maker_fee_rate,
        )
