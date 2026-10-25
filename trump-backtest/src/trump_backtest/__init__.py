"""Reproducible Trump-term ETF backtests."""

from trump_backtest.models import (
    AlignedMarketData,
    BacktestResult,
    DailyBar,
    Dividend,
    MomentumParams,
    PerformanceMetrics,
    TickerSeries,
)

__all__ = [
    "AlignedMarketData",
    "BacktestResult",
    "DailyBar",
    "Dividend",
    "MomentumParams",
    "PerformanceMetrics",
    "TickerSeries",
]

__version__ = "0.1.0"
