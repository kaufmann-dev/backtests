"""Massive acquisition, total-return construction, and deterministic caching."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from itertools import pairwise
from pathlib import Path
from typing import cast
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

from trump_backtest.models import AlignedMarketData, DailyBar, Dividend, TickerSeries

JsonObject = dict[str, object]


def _json_object(value: object, description: str) -> JsonObject:
    if not isinstance(value, dict):
        raise ValueError(f"{description} must be a JSON object")
    mapping = cast(dict[object, object], value)
    if not all(isinstance(key, str) for key in mapping):
        raise ValueError(f"{description} must have string keys")
    return cast(JsonObject, mapping)


def build_total_return_series(series: TickerSeries) -> tuple[float, ...]:
    """Return close-to-close total returns with cash credited on ex-dates."""

    cash_by_date: dict[date, float] = {}
    for item in series.dividends:
        cash_by_date[item.ex_date] = cash_by_date.get(item.ex_date, 0.0) + item.amount
    result = [0.0]
    for previous, current in pairwise(series.bars):
        distribution = cash_by_date.get(current.date, 0.0)
        result.append((current.close + distribution) / previous.close - 1.0)
    return tuple(result)


def align_series(series: tuple[TickerSeries, ...]) -> AlignedMarketData:
    if not series:
        raise ValueError("at least one ticker series is required")
    dates = tuple(bar.date for bar in series[0].bars)
    for item in series[1:]:
        item_dates = tuple(bar.date for bar in item.bars)
        if item_dates != dates:
            raise ValueError(f"{item.ticker} calendar does not match {series[0].ticker}")

    tickers = tuple(item.ticker for item in series)
    returns_by_ticker = tuple(build_total_return_series(item) for item in series)
    cash_maps = tuple(
        {
            ex_date: sum(
                dividend.amount for dividend in item.dividends if dividend.ex_date == ex_date
            )
            for ex_date in {dividend.ex_date for dividend in item.dividends}
        }
        for item in series
    )
    closes = tuple(tuple(item.bars[row].close for item in series) for row in range(len(dates)))
    dividends = tuple(
        tuple(cash_maps[column].get(session, 0.0) for column in range(len(series)))
        for session in dates
    )
    total_returns = tuple(
        tuple(returns_by_ticker[column][row] for column in range(len(series)))
        for row in range(len(dates))
    )
    return AlignedMarketData(
        dates=dates,
        tickers=tickers,
        closes=closes,
        dividends=dividends,
        total_returns=total_returns,
    )


class MassiveClient:
    """Small REST client for the two Massive endpoints required by the research."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.massive.com",
        timeout_seconds: float = 30.0,
    ) -> None:
        if not api_key:
            raise ValueError("a Massive API key is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _get(self, path_or_url: str, params: dict[str, str | int | bool]) -> JsonObject:
        base = (
            path_or_url if path_or_url.startswith("https://") else f"{self.base_url}{path_or_url}"
        )
        parsed = urlparse(base)
        query: dict[str, str] = dict(parse_qsl(parsed.query, keep_blank_values=True))
        for key, value in params.items():
            query[key] = str(value).lower() if isinstance(value, bool) else str(value)
        query["apiKey"] = self.api_key
        url = urlunparse(parsed._replace(query=urlencode(query)))
        request = Request(url, headers={"Accept": "application/json"})
        with urlopen(request, timeout=self.timeout_seconds) as response:
            raw_payload = cast(object, json.loads(response.read().decode("utf-8")))
        return _json_object(raw_payload, "Massive response")

    def fetch_ticker(self, ticker: str, start: date, end: date) -> TickerSeries:
        path = f"/v2/aggs/ticker/{ticker}/range/1/day/{start.isoformat()}/{end.isoformat()}"
        price_payload = self._get(
            path,
            {"adjusted": True, "sort": "asc", "limit": 50_000},
        )
        raw_bars = price_payload.get("results")
        if not isinstance(raw_bars, list) or not raw_bars:
            raise ValueError(f"Massive returned no daily bars for {ticker}")
        bars: list[DailyBar] = []
        for raw_value in cast(list[object], raw_bars):
            value = _json_object(raw_value, f"Massive bar for {ticker}")
            timestamp = value.get("t")
            close = value.get("c")
            open_price = value.get("o")
            if not isinstance(timestamp, (int, float)) or not isinstance(close, (int, float)):
                raise ValueError(f"Massive returned an incomplete bar for {ticker}")
            bars.append(
                DailyBar(
                    date=datetime.fromtimestamp(timestamp / 1000, tz=UTC).date(),
                    close=float(close),
                    open=float(open_price) if isinstance(open_price, (int, float)) else None,
                )
            )

        dividend_payload = self._get(
            "/stocks/v1/dividends",
            {
                "ticker": ticker,
                "ex_dividend_date.gte": start.isoformat(),
                "ex_dividend_date.lte": end.isoformat(),
                "sort": "ex_dividend_date.asc",
                "limit": 5_000,
            },
        )
        raw_dividends = dividend_payload.get("results", [])
        if not isinstance(raw_dividends, list):
            raise ValueError(f"Massive returned malformed dividends for {ticker}")
        dividends: list[Dividend] = []
        for raw_value in cast(list[object], raw_dividends):
            if not isinstance(raw_value, dict):
                continue
            dividend = _json_object(cast(object, raw_value), f"Massive dividend for {ticker}")
            raw_date = dividend.get("ex_dividend_date")
            raw_amount = dividend.get(
                "split_adjusted_cash_amount",
                dividend.get("cash_amount"),
            )
            if isinstance(raw_date, str) and isinstance(raw_amount, (int, float)):
                dividends.append(
                    Dividend(ex_date=date.fromisoformat(raw_date), amount=float(raw_amount))
                )
        return TickerSeries(ticker=ticker, bars=tuple(bars), dividends=tuple(dividends))

    def fetch_aligned(
        self,
        tickers: tuple[str, ...],
        start: date,
        end: date,
        *,
        workers: int = 8,
    ) -> AlignedMarketData:
        if workers <= 0:
            raise ValueError("workers must be positive")

        def fetch(ticker: str) -> TickerSeries:
            return self.fetch_ticker(ticker, start, end)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            fetched = tuple(executor.map(fetch, tickers))
        return align_series(fetched)


def save_market_data(data: AlignedMarketData, path: Path) -> None:
    payload: JsonObject = {
        "dates": [item.isoformat() for item in data.dates],
        "tickers": list(data.tickers),
        "closes": [list(row) for row in data.closes],
        "dividends": [list(row) for row in data.dividends],
        "total_returns": [list(row) for row in data.total_returns],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")


def _float_matrix(value: object, name: str) -> tuple[tuple[float, ...], ...]:
    if not isinstance(value, list):
        raise ValueError(f"cached {name} must be a list")
    rows: list[tuple[float, ...]] = []
    for row in cast(list[object], value):
        if not isinstance(row, list):
            raise ValueError(f"cached {name} contains a malformed row")
        row_items = cast(list[object], row)
        if not all(isinstance(item, (int, float)) for item in row_items):
            raise ValueError(f"cached {name} contains a non-numeric value")
        numeric_row = cast(list[int | float], row_items)
        rows.append(tuple(float(item) for item in numeric_row))
    return tuple(rows)


def load_market_data(path: Path) -> AlignedMarketData:
    decoded = cast(object, json.loads(path.read_text(encoding="utf-8")))
    raw = _json_object(decoded, "market-data cache")
    dates_value = raw.get("dates")
    tickers_value = raw.get("tickers")
    if not isinstance(dates_value, list):
        raise ValueError("cached dates are malformed")
    date_items = cast(list[object], dates_value)
    if not all(isinstance(item, str) for item in date_items):
        raise ValueError("cached dates are malformed")
    if not isinstance(tickers_value, list):
        raise ValueError("cached tickers are malformed")
    ticker_items = cast(list[object], tickers_value)
    if not all(isinstance(item, str) for item in ticker_items):
        raise ValueError("cached tickers are malformed")
    date_strings = cast(list[str], date_items)
    tickers = cast(list[str], ticker_items)
    return AlignedMarketData(
        dates=tuple(date.fromisoformat(item) for item in date_strings),
        tickers=tuple(tickers),
        closes=_float_matrix(raw.get("closes"), "closes"),
        dividends=_float_matrix(raw.get("dividends"), "dividends"),
        total_returns=_float_matrix(raw.get("total_returns"), "total_returns"),
    )
