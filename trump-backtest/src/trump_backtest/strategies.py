"""Future-known oracle and observable momentum allocation rules."""

from __future__ import annotations

from math import log

from trump_backtest.models import AlignedMarketData, MomentumParams
from trump_backtest.universe import BENCHMARK, CASH_PROXY

WeightRow = tuple[float, ...]
WeightMatrix = tuple[WeightRow, ...]


def _cash_weights(data: AlignedMarketData) -> WeightRow:
    cash_index = data.ticker_index(CASH_PROXY)
    return tuple(1.0 if index == cash_index else 0.0 for index in range(len(data.tickers)))


def _single_asset_weights(data: AlignedMarketData, asset_index: int) -> WeightRow:
    return tuple(1.0 if index == asset_index else 0.0 for index in range(len(data.tickers)))


def oracle_weights(data: AlignedMarketData) -> WeightMatrix:
    """At each close, select the asset with the best next-session return."""

    cash = _cash_weights(data)
    rows: list[WeightRow] = []
    for close_index in range(len(data.dates)):
        return_index = close_index + 1
        if return_index >= len(data.dates):
            rows.append(cash)
            continue
        winner = max(
            range(len(data.tickers)),
            key=lambda column: data.total_returns[return_index][column],
        )
        rows.append(_single_asset_weights(data, winner))
    return tuple(rows)


def buy_and_hold_weights(data: AlignedMarketData, ticker: str) -> WeightMatrix:
    row = _single_asset_weights(data, data.ticker_index(ticker))
    return tuple(row for _ in data.dates)


def _total_return_levels(data: AlignedMarketData) -> tuple[tuple[float, ...], ...]:
    levels: list[list[float]] = [[1.0 for _ in data.tickers]]
    for row in data.total_returns[1:]:
        previous = levels[-1]
        levels.append(
            [
                prior * (1.0 + period_return)
                for prior, period_return in zip(previous, row, strict=True)
            ]
        )
    return tuple(tuple(row) for row in levels)


def _simple_moving_average(
    data: AlignedMarketData,
    ticker_index: int,
    end_index: int,
    window: int,
) -> float:
    if window <= 0 or end_index - window + 1 < 0:
        raise ValueError("moving-average window is unavailable")
    start = end_index - window + 1
    return sum(data.closes[row][ticker_index] for row in range(start, end_index + 1)) / window


def momentum_weights(
    data: AlignedMarketData,
    params: MomentumParams,
    *,
    start_index: int = 0,
) -> WeightMatrix:
    """Return close-effective weights using information through the prior close.

    A row at index ``t`` is the allocation established at that session's close
    and earns the total return at row ``t + 1``.
    """

    if not 0 <= start_index < len(data.dates):
        raise ValueError("start_index is outside the market data")
    cash = _cash_weights(data)
    levels = _total_return_levels(data)
    benchmark_index = data.ticker_index(BENCHMARK)
    cash_index = data.ticker_index(CASH_PROXY)
    current = cash
    rows: list[WeightRow] = []

    for target_index in range(len(data.dates)):
        should_rebalance = target_index >= start_index and (
            (target_index - start_index) % params.rebalance == 0
        )
        if not should_rebalance:
            rows.append(current)
            continue

        signal_index = target_index - 1
        score_start = signal_index - params.lookback
        score_end = signal_index - params.skip
        gate_window = params.market_gate_window
        history_needed = max(
            params.lookback,
            params.trend,
            gate_window,
        )
        if signal_index < history_needed or score_start < 0 or score_end <= score_start:
            current = cash
            rows.append(current)
            continue

        if gate_window and data.closes[signal_index][benchmark_index] <= _simple_moving_average(
            data,
            benchmark_index,
            signal_index,
            gate_window,
        ):
            current = cash
            rows.append(current)
            continue

        candidates: list[tuple[float, int]] = []
        for ticker_index in range(len(data.tickers)):
            if ticker_index == cash_index:
                continue
            if params.trend and data.closes[signal_index][ticker_index] <= _simple_moving_average(
                data,
                ticker_index,
                signal_index,
                params.trend,
            ):
                continue
            start_level = levels[score_start][ticker_index]
            end_level = levels[score_end][ticker_index]
            if start_level > 0 and end_level > 0:
                candidates.append((log(end_level / start_level), ticker_index))

        if not candidates:
            current = cash
        else:
            _, winner = max(candidates, key=lambda item: (item[0], -item[1]))
            current = _single_asset_weights(data, winner)
        rows.append(current)
    return tuple(rows)
