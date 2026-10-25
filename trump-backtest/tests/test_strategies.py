from datetime import date, timedelta

from trump_backtest.models import AlignedMarketData, MomentumParams
from trump_backtest.strategies import momentum_weights, oracle_weights


def _market_data(
    returns: tuple[tuple[float, ...], ...],
    tickers: tuple[str, ...] = ("AAA", "BBB", "SPY", "BIL"),
) -> AlignedMarketData:
    dates = tuple(date(2025, 1, 21) + timedelta(days=index) for index in range(len(returns)))
    dividends = tuple(tuple(0.0 for _ in tickers) for _ in returns)
    levels: list[tuple[float, ...]] = []
    previous = [100.0 for _ in tickers]
    for row in returns:
        previous = [
            level * (1.0 + period_return)
            for level, period_return in zip(previous, row, strict=True)
        ]
        levels.append(tuple(previous))
    return AlignedMarketData(
        dates=dates,
        tickers=tickers,
        closes=tuple(levels),
        dividends=dividends,
        total_returns=returns,
    )


def test_oracle_selects_each_sessions_future_winner() -> None:
    data = _market_data(
        (
            (0.0, 0.0, 0.0, 0.0),
            (0.10, -0.05, 0.02, 0.001),
            (-0.20, 0.30, 0.02, 0.001),
        )
    )

    weights = oracle_weights(data)

    assert weights[0] == (1.0, 0.0, 0.0, 0.0)
    assert weights[1] == (0.0, 1.0, 0.0, 0.0)
    assert weights[2] == (0.0, 0.0, 0.0, 1.0)


def test_momentum_uses_prior_close_and_skips_recent_session() -> None:
    data = _market_data(
        (
            (0.0, 0.0, 0.0, 0.0),
            (0.10, 0.0, 0.02, 0.0),
            (0.10, 0.0, 0.02, 0.0),
            (-0.90, 0.50, 0.02, 0.0),
            (-0.50, 1.00, 0.02, 0.0),
        )
    )
    params = MomentumParams(
        lookback=3,
        skip=1,
        rebalance=1,
        trend=0,
        market_gate=False,
    )

    weights = momentum_weights(data, params)

    assert weights[:4] == ((0.0, 0.0, 0.0, 1.0),) * 4
    assert weights[4] == (1.0, 0.0, 0.0, 0.0)
