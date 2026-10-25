"""Command-line entry point for fetching and rerunning the research."""

from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path
from typing import cast

from trump_backtest.analysis import run_published_research
from trump_backtest.market_data import MassiveClient, load_market_data, save_market_data
from trump_backtest.universe import ETF_UNIVERSE


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trump-backtest")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch = subparsers.add_parser("fetch", help="fetch and cache Massive market data")
    fetch.add_argument("--start", type=date.fromisoformat, default=date(2021, 8, 2))
    fetch.add_argument("--end", type=date.fromisoformat, default=date.today())
    fetch.add_argument("--output", type=Path, default=Path("cache/market-data.json"))
    fetch.add_argument("--workers", type=int, default=8)

    run = subparsers.add_parser("run", help="run the published formulas from a cache")
    run.add_argument("--input", type=Path, default=Path("cache/market-data.json"))
    run.add_argument("--output", type=Path)
    run.add_argument("--cost-bps", type=float, default=5.0)
    return parser


def _fetch(namespace: argparse.Namespace) -> int:
    api_key = os.environ.get("MASSIVE_API_KEY")
    if not api_key:
        raise SystemExit("MASSIVE_API_KEY must be set for the fetch command")
    start = cast(date, namespace.start)
    end = cast(date, namespace.end)
    if end <= start:
        raise SystemExit("--end must be after --start")
    client = MassiveClient(
        api_key,
        base_url=os.environ.get("MASSIVE_BASE_URL", "https://api.massive.com"),
    )
    data = client.fetch_aligned(
        ETF_UNIVERSE,
        start,
        end,
        workers=cast(int, namespace.workers),
    )
    output = cast(Path, namespace.output)
    save_market_data(data, output)
    print(f"cached {len(data.dates)} sessions for {len(data.tickers)} ETFs at {output}")
    return 0


def _run(namespace: argparse.Namespace) -> int:
    data = load_market_data(cast(Path, namespace.input))
    result = run_published_research(
        data,
        cost_bps=cast(float, namespace.cost_bps),
    )
    rendered = json.dumps(result, indent=2, sort_keys=True)
    output = cast(Path | None, namespace.output)
    if output is None:
        print(rendered)
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(f"{rendered}\n", encoding="utf-8")
        print(f"wrote research results to {output}")
    return 0


def main() -> int:
    namespace = _parser().parse_args()
    command = cast(str, namespace.command)
    if command == "fetch":
        return _fetch(namespace)
    if command == "run":
        return _run(namespace)
    raise SystemExit(f"unknown command: {command}")
