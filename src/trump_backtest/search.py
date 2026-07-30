"""Finite parameter-grid evaluation for causal momentum rules."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from trump_backtest.engine import run_backtest
from trump_backtest.metrics import metrics_for_backtest
from trump_backtest.models import (
    AlignedMarketData,
    BacktestResult,
    MomentumParams,
    PerformanceMetrics,
)
from trump_backtest.strategies import momentum_weights


@dataclass(frozen=True, slots=True)
class SearchObservation:
    params: MomentumParams
    result: BacktestResult
    metrics: PerformanceMetrics


def parameter_grid(
    *,
    lookbacks: tuple[int, ...],
    skips: tuple[int, ...],
    rebalances: tuple[int, ...],
    trends: tuple[int, ...],
    market_gates: tuple[int | bool, ...],
) -> tuple[MomentumParams, ...]:
    params: list[MomentumParams] = []
    for lookback, skip, rebalance, trend, gate in product(
        lookbacks,
        skips,
        rebalances,
        trends,
        market_gates,
    ):
        if skip < lookback:
            params.append(
                MomentumParams(
                    lookback=lookback,
                    skip=skip,
                    rebalance=rebalance,
                    trend=trend,
                    market_gate=gate,
                )
            )
    return tuple(params)


def search_by_total_return(
    data: AlignedMarketData,
    candidates: tuple[MomentumParams, ...],
    *,
    start_index: int,
    end_index: int,
    cost_bps: float,
) -> tuple[SearchObservation, ...]:
    observations: list[SearchObservation] = []
    for params in candidates:
        weights = momentum_weights(data, params, start_index=start_index)
        result = run_backtest(
            data,
            weights,
            cost_bps=cost_bps,
            start_index=start_index,
            end_index=end_index,
        )
        observations.append(
            SearchObservation(
                params=params,
                result=result,
                metrics=metrics_for_backtest(result),
            )
        )
    return tuple(
        sorted(
            observations,
            key=lambda item: item.metrics.total_return,
            reverse=True,
        )
    )
