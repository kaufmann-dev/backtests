"""Published research formulas assembled from the reusable engine."""

from __future__ import annotations

from collections import Counter
from datetime import date
from math import sqrt
from statistics import stdev

from trump_backtest.engine import run_backtest
from trump_backtest.models import (
    AlignedMarketData,
    BacktestResult,
    MomentumParams,
    PerformanceMetrics,
)
from trump_backtest.strategies import (
    buy_and_hold_weights,
    momentum_weights,
    oracle_weights,
)
from trump_backtest.universe import BENCHMARK, CASH_PROXY


def _period_metrics(
    result: BacktestResult,
    start: date,
    end: date,
) -> PerformanceMetrics:
    if not result.returns:
        raise ValueError("research period has no returns")
    wealth = result.ending_wealth
    elapsed_years = (end - start).days / 365.25
    peak = 1.0
    drawdown = 0.0
    for level in result.wealth:
        peak = max(peak, level)
        drawdown = min(drawdown, level / peak - 1.0)
    return PerformanceMetrics(
        total_return=wealth - 1.0,
        cagr=wealth ** (1.0 / elapsed_years) - 1.0,
        annual_volatility=(stdev(result.returns) * sqrt(252) if len(result.returns) > 1 else 0.0),
        max_drawdown=drawdown,
    )


def _metric_payload(metrics: PerformanceMetrics) -> dict[str, object]:
    return {
        "total_return": metrics.total_return,
        "cagr": metrics.cagr,
        "annual_volatility": metrics.annual_volatility,
        "max_drawdown": metrics.max_drawdown,
    }


def _holding(data: AlignedMarketData, row: tuple[float, ...]) -> str:
    return data.tickers[max(range(len(row)), key=row.__getitem__)]


def _evaluate_momentum(
    data: AlignedMarketData,
    params: MomentumParams,
    start_index: int,
    end_index: int,
    cost_bps: float,
) -> tuple[BacktestResult, tuple[tuple[float, ...], ...]]:
    weights = momentum_weights(data, params, start_index=start_index)
    result = run_backtest(
        data,
        weights,
        cost_bps=cost_bps,
        start_index=start_index,
        end_index=end_index,
    )
    return result, weights


def run_published_research(
    data: AlignedMarketData,
    *,
    term_start: date = date(2025, 1, 21),
    pre_start: date = date(2022, 8, 2),
    pre_end: date = date(2025, 1, 17),
    cost_bps: float = 5.0,
) -> dict[str, object]:
    """Evaluate the oracle, fitted champion, and continuation formula."""

    term_start_index = data.date_index(term_start)
    term_end_index = len(data.dates) - 1
    pre_start_index = data.date_index(pre_start)
    pre_end_index = data.date_index(pre_end)
    if pre_end_index >= term_start_index:
        raise ValueError("pre-term period must end before the Trump-term period")

    benchmark_weights = buy_and_hold_weights(data, BENCHMARK)
    benchmark_term = run_backtest(
        data,
        benchmark_weights,
        cost_bps=cost_bps,
        start_index=term_start_index,
        end_index=term_end_index,
    )
    benchmark_pre = run_backtest(
        data,
        benchmark_weights,
        cost_bps=cost_bps,
        start_index=pre_start_index,
        end_index=pre_end_index,
    )

    future_weights = oracle_weights(data)
    oracle_no_cost = run_backtest(
        data,
        future_weights,
        start_index=term_start_index,
        end_index=term_end_index,
    )
    oracle_with_cost = run_backtest(
        data,
        future_weights,
        cost_bps=cost_bps,
        start_index=term_start_index,
        end_index=term_end_index,
    )
    oracle_picks = Counter(
        _holding(data, future_weights[index]) for index in range(term_start_index, term_end_index)
    )

    best_static_ticker = ""
    best_static_result: BacktestResult | None = None
    for ticker in data.tickers:
        if ticker == CASH_PROXY:
            continue
        candidate = run_backtest(
            data,
            buy_and_hold_weights(data, ticker),
            start_index=term_start_index,
            end_index=term_end_index,
        )
        if best_static_result is None or candidate.ending_wealth > best_static_result.ending_wealth:
            best_static_ticker = ticker
            best_static_result = candidate
    if best_static_result is None:
        raise ValueError("no risk assets are available for static comparison")

    champion_params = MomentumParams(
        lookback=42,
        skip=0,
        rebalance=10,
        trend=0,
        market_gate=200,
    )
    champion_term, champion_term_weights = _evaluate_momentum(
        data,
        champion_params,
        term_start_index,
        term_end_index,
        cost_bps,
    )
    champion_pre, _ = _evaluate_momentum(
        data,
        champion_params,
        pre_start_index,
        pre_end_index,
        cost_bps,
    )

    continuation_params = MomentumParams(
        lookback=252,
        skip=21,
        rebalance=21,
    )
    continuation_term, continuation_term_weights = _evaluate_momentum(
        data,
        continuation_params,
        term_start_index,
        term_end_index,
        cost_bps,
    )
    continuation_pre, _ = _evaluate_momentum(
        data,
        continuation_params,
        pre_start_index,
        pre_end_index,
        cost_bps,
    )
    last_rebalance_index = (
        term_start_index
        + ((term_end_index - term_start_index) // continuation_params.rebalance)
        * continuation_params.rebalance
    )
    sessions_until_rebalance = continuation_params.rebalance - (
        (term_end_index - term_start_index) % continuation_params.rebalance
    )

    return {
        "data": {
            "provider": "Massive",
            "available_start": data.dates[0].isoformat(),
            "term_start": term_start.isoformat(),
            "term_end": data.dates[term_end_index].isoformat(),
            "term_trading_sessions": term_end_index - term_start_index + 1,
            "universe": list(data.tickers),
        },
        "benchmark": {
            "ticker": BENCHMARK,
            "term": _metric_payload(
                _period_metrics(benchmark_term, term_start, data.dates[term_end_index])
            ),
            "pre_term": _metric_payload(_period_metrics(benchmark_pre, pre_start, pre_end)),
        },
        "unconstrained": {
            "mathematical_optimum": ("unbounded when leverage or shorting is unrestricted"),
            "oracle_1x_no_cost": _metric_payload(
                _period_metrics(oracle_no_cost, term_start, data.dates[term_end_index])
            ),
            "oracle_1x_with_cost": {
                **_metric_payload(
                    _period_metrics(
                        oracle_with_cost,
                        term_start,
                        data.dates[term_end_index],
                    )
                ),
                "switches": oracle_with_cost.total_turnover,
            },
            "most_selected": dict(oracle_picks.most_common()),
            "best_static": {
                "ticker": best_static_ticker,
                **_metric_payload(
                    _period_metrics(
                        best_static_result,
                        term_start,
                        data.dates[term_end_index],
                    )
                ),
            },
        },
        "causal_hindsight_champion": {
            "params": {
                "lookback": 42,
                "skip": 0,
                "rebalance": 10,
                "market_gate": 200,
            },
            "searched_candidates": 28_800,
            "term": _metric_payload(
                _period_metrics(champion_term, term_start, data.dates[term_end_index])
            ),
            "pre_term": _metric_payload(_period_metrics(champion_pre, pre_start, pre_end)),
            "current_holding": _holding(
                data,
                champion_term_weights[term_end_index],
            ),
        },
        "continuation_candidate": {
            "params": {
                "lookback": 252,
                "skip": 21,
                "rebalance": 21,
            },
            "formula": "ln(TR[t-21] / TR[t-252])",
            "searched_candidates": 7_200,
            "term": _metric_payload(
                _period_metrics(
                    continuation_term,
                    term_start,
                    data.dates[term_end_index],
                )
            ),
            "pre_term": _metric_payload(_period_metrics(continuation_pre, pre_start, pre_end)),
            "current_holding": _holding(
                data,
                continuation_term_weights[term_end_index],
            ),
            "current_holding_effective_date": data.dates[last_rebalance_index].isoformat(),
            "current_signal_date": data.dates[last_rebalance_index - 1].isoformat(),
            "additional_sessions_until_rebalance": sessions_until_rebalance,
        },
    }
