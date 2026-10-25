"""Portfolio accounting with close-effective weights."""

from __future__ import annotations

from math import isclose

from trump_backtest.models import AlignedMarketData, BacktestResult
from trump_backtest.universe import CASH_PROXY


def half_l1_turnover(previous: tuple[float, ...], current: tuple[float, ...]) -> float:
    if len(previous) != len(current):
        raise ValueError("weight vectors must have equal length")
    return 0.5 * sum(abs(new - old) for old, new in zip(previous, current, strict=True))


def _validate_weights(
    data: AlignedMarketData,
    weights: tuple[tuple[float, ...], ...],
) -> None:
    if len(weights) != len(data.dates):
        raise ValueError("weights must have one row per market date")
    for row in weights:
        if len(row) != len(data.tickers):
            raise ValueError("weight rows must match the ticker count")
        if any(value < 0 for value in row):
            raise ValueError("weights must be long-only")
        if not isclose(sum(row), 1.0, abs_tol=1e-9):
            raise ValueError("each weight row must sum to one")


def run_backtest(
    data: AlignedMarketData,
    weights: tuple[tuple[float, ...], ...],
    *,
    cost_bps: float = 0.0,
    start_index: int = 0,
    end_index: int | None = None,
) -> BacktestResult:
    """Apply weights set at close ``t`` to the return from close ``t`` to ``t+1``."""

    _validate_weights(data, weights)
    if cost_bps < 0:
        raise ValueError("cost_bps cannot be negative")
    final_index = len(data.dates) - 1 if end_index is None else end_index
    if not 0 <= start_index < final_index < len(data.dates):
        raise ValueError("backtest indices must contain at least one holding period")

    cash_index = data.ticker_index(CASH_PROXY)
    previous = tuple(1.0 if index == cash_index else 0.0 for index in range(len(data.tickers)))
    period_returns: list[float] = []
    wealth: list[float] = [1.0]
    turnover: list[float] = []
    costs: list[float] = []
    applied_weights: list[tuple[float, ...]] = []

    for close_index in range(start_index, final_index):
        current = weights[close_index]
        one_way = half_l1_turnover(previous, current)
        cost = one_way * cost_bps / 10_000.0
        next_returns = data.total_returns[close_index + 1]
        gross_return = sum(
            weight * asset_return
            for weight, asset_return in zip(current, next_returns, strict=True)
        )
        net_return = (1.0 - cost) * (1.0 + gross_return) - 1.0
        period_returns.append(net_return)
        wealth.append(wealth[-1] * (1.0 + net_return))
        turnover.append(one_way)
        costs.append(cost)
        applied_weights.append(current)
        previous = current

    return BacktestResult(
        returns=tuple(period_returns),
        wealth=tuple(wealth),
        weights=tuple(applied_weights),
        turnover=tuple(turnover),
        costs=tuple(costs),
    )
