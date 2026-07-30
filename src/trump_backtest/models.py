"""Typed domain models for market data and backtest results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from itertools import pairwise
from math import isfinite


def _require_finite(value: float, name: str) -> None:
    if not isfinite(value):
        raise ValueError(f"{name} must be finite")


@dataclass(frozen=True, slots=True)
class DailyBar:
    date: date
    close: float
    open: float | None = None

    def __post_init__(self) -> None:
        _require_finite(self.close, "close")
        if self.close <= 0:
            raise ValueError("close must be positive")
        if self.open is not None:
            _require_finite(self.open, "open")
            if self.open <= 0:
                raise ValueError("open must be positive")


@dataclass(frozen=True, slots=True)
class Dividend:
    ex_date: date
    amount: float

    def __post_init__(self) -> None:
        _require_finite(self.amount, "dividend amount")
        if self.amount < 0:
            raise ValueError("dividend amount cannot be negative")


@dataclass(frozen=True, slots=True)
class TickerSeries:
    ticker: str
    bars: tuple[DailyBar, ...]
    dividends: tuple[Dividend, ...] = ()

    def __post_init__(self) -> None:
        if not self.ticker or self.ticker != self.ticker.upper():
            raise ValueError("ticker must be non-empty uppercase text")
        if not self.bars:
            raise ValueError(f"{self.ticker} has no daily bars")
        bar_dates = tuple(bar.date for bar in self.bars)
        if any(current <= previous for previous, current in pairwise(bar_dates)):
            raise ValueError(f"{self.ticker} bar dates must be strictly increasing")
        dividend_dates = tuple(item.ex_date for item in self.dividends)
        if any(current < previous for previous, current in pairwise(dividend_dates)):
            raise ValueError(f"{self.ticker} dividends must be date ordered")


@dataclass(frozen=True, slots=True)
class AlignedMarketData:
    """Rows are sessions and columns follow ``tickers``."""

    dates: tuple[date, ...]
    tickers: tuple[str, ...]
    closes: tuple[tuple[float, ...], ...]
    dividends: tuple[tuple[float, ...], ...]
    total_returns: tuple[tuple[float, ...], ...]

    def __post_init__(self) -> None:
        if not self.dates or not self.tickers:
            raise ValueError("market data needs dates and tickers")
        if len(set(self.tickers)) != len(self.tickers):
            raise ValueError("tickers must be unique")
        if any(current <= previous for previous, current in pairwise(self.dates)):
            raise ValueError("market dates must be strictly increasing")
        expected_rows = len(self.dates)
        if not (
            len(self.closes) == len(self.dividends) == len(self.total_returns) == expected_rows
        ):
            raise ValueError("market matrices must match the date count")
        width = len(self.tickers)
        for name, matrix in (
            ("closes", self.closes),
            ("dividends", self.dividends),
            ("total_returns", self.total_returns),
        ):
            if any(len(row) != width for row in matrix):
                raise ValueError(f"{name} rows must match the ticker count")
            if any(not isfinite(value) for row in matrix for value in row):
                raise ValueError(f"{name} must contain only finite values")
        if any(value <= 0 for row in self.closes for value in row):
            raise ValueError("closes must be positive")

    def ticker_index(self, ticker: str) -> int:
        try:
            return self.tickers.index(ticker)
        except ValueError as error:
            raise KeyError(f"ticker {ticker!r} is not in the aligned data") from error

    def date_index(self, target: date) -> int:
        try:
            return self.dates.index(target)
        except ValueError as error:
            raise KeyError(f"date {target.isoformat()} is not in the aligned data") from error


@dataclass(frozen=True, slots=True)
class MomentumParams:
    lookback: int
    skip: int
    rebalance: int
    trend: int = 0
    market_gate: int | bool = False

    def __post_init__(self) -> None:
        if self.lookback <= 0:
            raise ValueError("lookback must be positive")
        if self.skip < 0 or self.skip >= self.lookback:
            raise ValueError("skip must be non-negative and shorter than lookback")
        if self.rebalance <= 0:
            raise ValueError("rebalance must be positive")
        if self.trend < 0:
            raise ValueError("trend cannot be negative")
        gate = int(self.market_gate)
        if gate < 0:
            raise ValueError("market gate cannot be negative")

    @property
    def market_gate_window(self) -> int:
        if self.market_gate is True:
            return 200
        return int(self.market_gate)


@dataclass(frozen=True, slots=True)
class BacktestResult:
    returns: tuple[float, ...]
    wealth: tuple[float, ...]
    weights: tuple[tuple[float, ...], ...]
    turnover: tuple[float, ...]
    costs: tuple[float, ...]

    @property
    def ending_wealth(self) -> float:
        return self.wealth[-1] if self.wealth else 1.0

    @property
    def total_turnover(self) -> float:
        return sum(self.turnover)


@dataclass(frozen=True, slots=True)
class PerformanceMetrics:
    total_return: float
    cagr: float
    annual_volatility: float
    max_drawdown: float
    sharpe: float | None = None
