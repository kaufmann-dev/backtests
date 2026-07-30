"""Performance statistics used by reports and strategy search."""

from __future__ import annotations

from math import sqrt
from statistics import fmean, stdev

from trump_backtest.models import BacktestResult, PerformanceMetrics


def calculate_metrics(
    returns: tuple[float, ...],
    *,
    periods_per_year: int = 252,
    risk_free_returns: tuple[float, ...] | None = None,
) -> PerformanceMetrics:
    if not returns:
        raise ValueError("at least one return is required")
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    if any(value <= -1.0 for value in returns):
        raise ValueError("returns cannot lose more than 100% in one period")

    wealth = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for value in returns:
        wealth *= 1.0 + value
        peak = max(peak, wealth)
        max_drawdown = min(max_drawdown, wealth / peak - 1.0)
    total_return = wealth - 1.0
    years = len(returns) / periods_per_year
    cagr = wealth ** (1.0 / years) - 1.0
    annual_volatility = stdev(returns) * sqrt(periods_per_year) if len(returns) > 1 else 0.0

    sharpe: float | None = None
    if risk_free_returns is not None:
        if len(risk_free_returns) != len(returns):
            raise ValueError("risk-free returns must align with strategy returns")
        excess = tuple(
            strategy - risk_free
            for strategy, risk_free in zip(returns, risk_free_returns, strict=True)
        )
        excess_volatility = stdev(excess) if len(excess) > 1 else 0.0
        sharpe = (
            fmean(excess) / excess_volatility * sqrt(periods_per_year) if excess_volatility else 0.0
        )
    return PerformanceMetrics(
        total_return=total_return,
        cagr=cagr,
        annual_volatility=annual_volatility,
        max_drawdown=max_drawdown,
        sharpe=sharpe,
    )


def metrics_for_backtest(
    result: BacktestResult,
    *,
    periods_per_year: int = 252,
    risk_free_returns: tuple[float, ...] | None = None,
) -> PerformanceMetrics:
    return calculate_metrics(
        result.returns,
        periods_per_year=periods_per_year,
        risk_free_returns=risk_free_returns,
    )
