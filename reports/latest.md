# Trump-to-date unconstrained backtest

Calculated on July 30, 2026 from Massive daily bars and cash distributions. Donald Trump's inauguration was January 20, 2025, when U.S. markets were closed; the common executable starting close is therefore January 21, 2025.

## Direct answer

A literally unconstrained return maximum does not exist. If leverage or shorting is unlimited, exposure can be increased without bound on any future-known winning trade.

The finite illustration below adds only two boundaries: one-times capital and long-only positions within the declared 33-ETF universe. Its hindsight formula is:

```text
i*(t) = argmax_i [TR_i(t + 1) / TR_i(t) - 1]
w_i(t) = 1 when i = i*(t), otherwise 0
W(T) = product_t [1 + max_i r_i(t + 1)]
```

In plain language: at every close, use tomorrow's prices to put everything into tomorrow's best ETF. This is the highest possible one-times long-only daily result in the tested universe, but it is an oracle—not an investment strategy.

| Trump-term result              |  Total return |        CAGR | Volatility | Max drawdown | $10,000 becomes |
| ------------------------------ | ------------: | ----------: | ---------: | -----------: | --------------: |
| SPY total return               |        25.03% |      15.84% |     17.71% |      -18.76% |         $12,503 |
| Best static ETF: SMH           |       106.01% |           — |          — |            — |         $20,601 |
| Causal hindsight champion      |       274.57% |     138.48% |     50.82% |      -37.15% |         $37,457 |
| Daily oracle, 5 bps per switch | 6,044,392.60% | 140,068.91% |     31.66% |       -0.04% |    $604,449,260 |
| Daily oracle, no costs         | 7,175,529.07% | 156,820.91% |     31.66% |        0.00% |    $717,562,907 |

The oracle switched 343 times in 382 holding sessions. Its most frequent winners were URA on 60 sessions, GDX on 48, SLV on 44, SMH on 34, COPX on 31, and XLE on 29. That extraordinary compounding is precisely the value of information from the future.

## Best formula fitted to the Trump period

The best causal member of a 28,800-rule search was:

```text
score_i(t) = ln[TR_i(t) / TR_i(t - 42)]

Every 10 trading sessions:
  if SPY(t) > SMA_200(SPY, t):
      hold 100% of the ETF with the highest score
  else:
      hold 100% BIL
```

Signals use data through the prior close, the new position becomes effective at the next close, and each one-way portfolio turnover costs 5 basis points.

It returned 274.57% versus SPY's 25.03%, but this is severe parameter-selection overfit. The same rule returned only 7.42% from August 2, 2022 through January 17, 2025, while SPY returned 51.84%. Its current fitted-rule holding is XLV, effective July 28, 2026.

## Formula with the strongest continuation evidence

Among 7,200 slower candidates, the return-first rule with the strongest balanced excess growth before and during the term was classic 12-to-1-month cross-sectional momentum:

```text
M_i(t) = ln[TR_i(t - 21) / TR_i(t - 252)]

Every 21 trading sessions:
  hold 100% of the ETF with the highest M_i(t)
```

The 21-session skip prevents the score from chasing the most recent month. The signal is delayed one session and costs 5 basis points per one-way turnover.

| Evaluation period           | Formula return | Formula CAGR | SPY return | SPY CAGR | Formula volatility | Formula max drawdown |
| --------------------------- | -------------: | -----------: | ---------: | -------: | -----------------: | -------------------: |
| Aug. 2, 2022–Jan. 17, 2025  |         75.21% |       25.59% |     51.84% |   18.49% |             31.58% |              -26.33% |
| Jan. 21, 2025–July 30, 2026 |         35.02% |       21.85% |     25.03% |   15.84% |             47.97% |              -57.02% |

The current continuation holding is **SMH**, selected from the July 23, 2026 signal and effective July 24. Under the fixed schedule, reevaluate after 17 additional completed trading sessions beyond the July 30 cutoff. If this rule is used as the answer to “until Trump is out of office,” freeze the formula and universe through the last trading session before January 20, 2029; changing parameters after losses would invalidate the backtest.

This is not a low-risk recommendation. It holds one ETF at a time, its observed Trump-term drawdown was 57.02%, and the selection process saw the evaluation data. No diversified, risk-controlled candidate in the tested family both beat SPY in the pre-term and Trump-term windows while keeping drawdown and volatility within 1.5 times SPY. SPY is the stronger choice if drawdown control matters more than maximizing the chance of raw outperformance.

## Backtest contract and limitations

- Universe: SPY, QQQ, IWM, DIA, XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY, KRE, IYT, XME, ITA, SMH, GLD, GDX, SLV, DBA, COPX, URA, UUP, EFA, EEM, VNQ, HYG, TLT, IEF, SHY, and BIL.
- Massive adjusted daily closes were used for splits; split-adjusted cash distributions were added on ex-dividend dates and reinvested.
- ETF expenses are embedded in traded prices. Taxes are excluded.
- Implementable rules and SPY pay 5 basis points per one-way turnover. The oracle is shown both before and after that simplified cost.
- The available Massive price history begins August 2, 2021, so pre-term evidence is limited.
- The fixed surviving ETF universe creates survivorship and theme-selection bias.
- Results are research, not a guarantee or individualized investment advice.
