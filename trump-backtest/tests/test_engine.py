from datetime import date, timedelta

import pytest

from trump_backtest.engine import half_l1_turnover, run_backtest
from trump_backtest.models import AlignedMarketData


def _market_data(returns: tuple[tuple[float, ...], ...]) -> AlignedMarketData:
    tickers = ("AAA", "BIL")
    dates = tuple(date(2025, 1, 21) + timedelta(days=index) for index in range(len(returns)))
    zeroes = tuple((0.0, 0.0) for _ in returns)
    closes = tuple((100.0, 100.0) for _ in returns)
    return AlignedMarketData(
        dates=dates,
        tickers=tickers,
        closes=closes,
        dividends=zeroes,
        total_returns=returns,
    )


def test_half_l1_turnover_counts_a_complete_switch_once() -> None:
    assert half_l1_turnover((0.0, 1.0), (1.0, 0.0)) == pytest.approx(1.0)
    assert half_l1_turnover((0.25, 0.75), (0.75, 0.25)) == pytest.approx(0.5)


def test_backtest_charges_switch_from_bil_at_one_way_turnover() -> None:
    data = _market_data(((0.0, 0.0), (0.10, 0.0), (0.0, 0.0)))
    weights = ((1.0, 0.0), (1.0, 0.0), (1.0, 0.0))

    result = run_backtest(data, weights, cost_bps=100.0)

    assert result.turnover == pytest.approx((1.0, 0.0))
    assert result.costs == pytest.approx((0.01, 0.0))
    assert result.returns == pytest.approx((0.089, 0.0))
    assert result.ending_wealth == pytest.approx(1.089)
