# Weekly Volatility-Targeted S&P 500 Strategy

## Purpose

This strategy adjusts broad S&P 500 exposure once per week using realized volatility and a slow trend filter. It is designed to reduce leverage as market risk rises without relying on discretionary predictions, trailing-stop optimization, or perfect crisis timing.

It is not expected to exit at market peaks. Its objective is to participate in sustained equity growth while reducing exposure during sufficiently volatile or persistent declines.

## Recommended implementation

Use the final trading session of each week, normally Friday:

1. At approximately 3:55 p.m. U.S. Eastern time, obtain a live S&P 500 level or a liquid S&P 500 ETF price.
2. Treat that value as an estimated closing price.
3. Update the 20-session realized-volatility estimate and 200-session simple moving average.
4. Calculate the new target exposure using the rules below.
5. Rebalance during the final minutes of the session, following the broker's order deadlines and execution rules.
6. Hold the resulting exposure until the next weekly rebalance.

The official closing level cannot be known before an exact closing execution. The 3:55 p.m. value is therefore an approximation. The backtest's close-proxy result should be treated as an optimistic estimate, while the one-session-delayed result provides a conservative benchmark.

## Signal calculation

Let `P[t]` be the latest S&P 500 level and let `r[t]` be its close-to-close return:

```text
r[t] = P[t] / P[t - 1] - 1
```

Calculate annualized realized volatility from the latest 20 returns using the sample standard deviation:

```text
volatility = sample_stddev(r[t - 19] ... r[t]) * sqrt(252)
```

Calculate the 200-session simple moving average:

```text
sma_200 = mean(P[t - 199] ... P[t])
```

Start with a 15% volatility target and constrain exposure to 0.5–1.5 times account equity:

```text
target_exposure = clamp(0.15 / volatility, 0.50, 1.50)
```

Apply the trend safeguard:

```text
if P[t] < sma_200:
    target_exposure = min(target_exposure, 0.75)

    if volatility > 0.30:
        target_exposure = 0.00
```

The calculated exposure takes effect after the rebalance. Do not revise it between scheduled weekly calculations unless the implementation has a separately documented operational emergency procedure.

## Exposure examples

- 10% realized volatility produces 1.50x exposure.
- 15% realized volatility produces 1.00x exposure.
- 20% realized volatility produces 0.75x exposure.
- 30% realized volatility produces 0.50x exposure when the index is above its moving average.
- A price below the 200-session average caps exposure at 0.75x.
- A price below the average combined with volatility above 30% produces 0x exposure.

## Portfolio construction

Exposure can be implemented with index futures, a margin account, or a combination of unleveraged and daily 2x funds. The implementation must account for financing, product expenses, tracking differences, taxes, and the possibility of forced liquidation.

For an illustrative combination of a 1x fund, a 2x daily fund, and cash:

```text
if target_exposure == 0:
    cash_weight = 1
    one_x_weight = 0
    two_x_weight = 0

if 0 < target_exposure < 1:
    cash_weight = 1 - target_exposure
    one_x_weight = target_exposure
    two_x_weight = 0

if 1 <= target_exposure <= 1.5:
    cash_weight = 0
    one_x_weight = 2 - target_exposure
    two_x_weight = target_exposure - 1
```

This allocation produces the requested nominal exposure while limiting the fraction held in the daily 2x product. Actual portfolio behavior will differ because of product expenses, daily reset mechanics, taxes, and tracking error. The SEC warns that leveraged ETFs target daily results and can diverge substantially from the stated multiple over longer periods: <https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-alerts/sec>

## Executable pseudocode

```text
on the final trading session of each week:
    estimated_close = obtain_market_value_near_15_55_ET()
    closes = replace_latest_close_with(estimated_close)

    returns_20 = latest_20_close_to_close_returns(closes)
    volatility = sample_stddev(returns_20) * sqrt(252)
    sma_200 = mean(latest_200_closes(closes))

    exposure = clamp(0.15 / volatility, 0.50, 1.50)

    if estimated_close < sma_200:
        exposure = min(exposure, 0.75)

        if volatility > 0.30:
            exposure = 0.00

    rebalance_portfolio_to(exposure)
```

Persist the calculation inputs, output exposure, order details, fills, and any errors for every rebalance. Use a fixed price source and a fixed definition of adjusted historical data when validating the implementation.

## Backtest definition

The strategy was evaluated from December 20, 1957 through August 4, 2026 using the S&P 500 price index. The first 200 observations were reserved for the moving-average warm-up.

The test used:

- Weekly exposure changes.
- Signals calculated only from completed or estimated-current observations.
- A 15% volatility target.
- Exposure bounded between 0.5x and 1.5x before the trend safeguard.
- Zero return on uninvested cash.
- No dividends, taxes, management fees, financing costs, or leveraged-product tracking error.
- A sensitivity charge of two basis points per unit of exposure changed.

Historical data came from the OpenIntro S&P 500 series through December 2018 and the Federal Reserve Economic Data S&P 500 series thereafter:

- <https://www.openintro.org/data/index.php?data=sp500_1950_2018>
- <https://fred.stlouisfed.org/series/SP500>

### Close-proxy result

This version approximates a 3:55 p.m. calculation and same-session rebalance using the official weekly close.

- Compound annual growth rate: 9.01%.
- Ending wealth multiple: 373.11x.
- Maximum drawdown: 50.32%.
- Annualized volatility: 13.98%.
- Worst daily return: 10.58% loss on October 19, 1987.
- Average exposure: 1.09x.
- Total exposure turnover: 294.81x across the full period.
- Rebalance changes: 2,016.

### One-session-delayed result

This version waits for the completed weekly close, retains the old exposure through the next session, and rebalances at that following close.

- Compound annual growth rate: 8.50%.
- Ending wealth multiple: 270.50x.
- Maximum drawdown: 49.10%.
- Annualized volatility: 14.20%.
- Worst daily return: 15.89% loss on October 19, 1987.
- Average exposure: 1.09x.

### Unleveraged benchmark

Continuous 1x S&P 500 price-index exposure over the same period produced:

- Compound annual growth rate: 7.99%.
- Ending wealth multiple: 195.96x.
- Maximum drawdown: 56.78%.

## Interpretation

The close-proxy implementation produced the strongest result. It earned approximately 0.51 percentage points more per year than the delayed implementation, although its maximum drawdown was about 1.2 percentage points worse. Both versions outperformed the unleveraged price index while experiencing a smaller historical maximum drawdown.

The strategy did not eliminate severe losses. The close-proxy version lost approximately 45.77% during the dot-com collapse and its maximum drawdown exceeded 50%. Its strongest defensive behavior occurred during the global financial crisis and the COVID-19 crash, when volatility rose rapidly and the trend filter reduced exposure.

The evidence supports using the 3:55 p.m. approximation when it can be executed consistently. An implementation that cannot calculate and trade near the close should use the delayed rule and should expect performance closer to the conservative backtest.

## Operational controls

- Hard-code 1.5x as the maximum exposure; do not override it manually.
- Do not increase exposure between scheduled weekly calculations.
- Validate that at least 201 consistent closing observations are available before calculating a signal.
- Reject calculations containing missing, duplicated, stale, or nonpositive prices.
- Verify that realized volatility is finite and positive.
- Record the intended exposure before submitting orders.
- Confirm fills and compute realized exposure after trading.
- Define broker-specific behavior for rejected, partially filled, or delayed orders.
- Keep enough liquidity to prevent forced liquidation during gaps and market closures.
- Test financing costs and leveraged-product tracking error before using live capital.

## Limitations

This is a historical simulation, not a guarantee. It uses one equity market and one realized sequence of crises. The official-close proxy cannot reproduce an exact 3:55 p.m. signal or fill. A daily leveraged product may materially underperform a frictionless leveraged index because of financing, expenses, volatility drag, taxes, and tracking error.

Volatility management has academic support, but published evidence does not establish that this exact parameterization will continue to outperform. See Moreira and Muir, *Volatility-Managed Portfolios*: <https://www.nber.org/papers/w22208>

