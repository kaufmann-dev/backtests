from datetime import date

import pytest

from trump_backtest.market_data import align_series, build_total_return_series
from trump_backtest.models import DailyBar, Dividend, TickerSeries


def test_total_return_reinvests_cash_dividend_on_ex_date() -> None:
    series = TickerSeries(
        ticker="AAA",
        bars=(
            DailyBar(date=date(2025, 1, 21), close=100.0),
            DailyBar(date=date(2025, 1, 22), close=98.0),
        ),
        dividends=(Dividend(ex_date=date(2025, 1, 22), amount=5.0),),
    )

    returns = build_total_return_series(series)

    assert returns == pytest.approx((0.0, 0.03))


def test_alignment_rejects_different_trading_calendars() -> None:
    first = TickerSeries(
        ticker="AAA",
        bars=(
            DailyBar(date=date(2025, 1, 21), close=100.0),
            DailyBar(date=date(2025, 1, 22), close=101.0),
        ),
        dividends=(),
    )
    second = TickerSeries(
        ticker="BBB",
        bars=(
            DailyBar(date=date(2025, 1, 21), close=100.0),
            DailyBar(date=date(2025, 1, 23), close=101.0),
        ),
        dividends=(),
    )

    with pytest.raises(ValueError, match="calendar"):
        align_series((first, second))


def test_series_rejects_duplicate_or_out_of_order_sessions() -> None:
    with pytest.raises(ValueError, match="strictly increasing"):
        TickerSeries(
            ticker="AAA",
            bars=(
                DailyBar(date=date(2025, 1, 22), close=100.0),
                DailyBar(date=date(2025, 1, 21), close=101.0),
            ),
            dividends=(),
        )
