import pytest

from trump_backtest.metrics import calculate_metrics


def test_metrics_use_compounding_sample_volatility_and_peak_drawdown() -> None:
    metrics = calculate_metrics((0.10, -0.10), periods_per_year=2)

    assert metrics.total_return == pytest.approx(-0.01)
    assert metrics.cagr == pytest.approx(-0.01)
    assert metrics.annual_volatility == pytest.approx(0.20)
    assert metrics.max_drawdown == pytest.approx(-0.10)
