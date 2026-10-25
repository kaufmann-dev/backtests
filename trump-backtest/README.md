# Trump Backtest

Reproducible ETF backtests for the current Trump administration. The project compares a future-known oracle, a Trump-period-fitted momentum rule, and a frozen 12-to-1-month momentum continuation candidate against SPY total return.

The published research is deliberately explicit about its limits: the oracle cannot be traded, the continuation candidate is concentrated, and no backtest guarantees future outperformance. See [the latest report](reports/latest.md) for the methodology, results, costs, and drawdown caveats.

## Run the research

Prerequisites:

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/)
- A Massive API key with access to U.S. daily aggregate bars and dividends

Install the project and set the API key:

```sh
uv sync --extra dev
export MASSIVE_API_KEY="your-api-key"
```

Fetch the fixed ETF universe into the ignored local cache, then calculate the published formulas:

```sh
uv run trump-backtest fetch --end 2026-07-30
uv run trump-backtest run --output artifacts/recomputed.json
```

The first command writes `cache/market-data.json`; the second reads that cache and writes machine-readable research results. Use a completed market date for `--end` so results do not include a partial session.

## What it evaluates

- A 1× long-only daily oracle that selects the next session's best ETF. This is a hindsight ceiling, not an implementable strategy.
- A causal 42-session momentum rule, rebalanced every 10 sessions with an SPY 200-session trend gate. Its parameters are selected using the Trump-period data and are therefore overfit by construction.
- A 12-to-1-month cross-sectional momentum rule, rebalanced every 21 sessions. It holds one ETF at a time and is the project's return-first continuation candidate.

All causal rules use data through the prior close, become effective at the next close, reinvest split-adjusted cash distributions, and apply 5 basis points per one-way turnover. The universe is fixed in [`src/trump_backtest/universe.py`](src/trump_backtest/universe.py).

## Results

- [Human-readable report](reports/latest.md)
- [Machine-readable snapshot](artifacts/latest-results.json)

The included snapshot uses Massive data from August 2, 2021 through July 30, 2026. Re-running with a different cutoff updates the output; it does not change the frozen formula definitions.

## Development checks

```sh
uv run pyright
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv build
```
