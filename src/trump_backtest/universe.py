"""The fixed ETF universe used by the published backtest."""

ETF_UNIVERSE: tuple[str, ...] = (
    "SPY",
    "QQQ",
    "IWM",
    "DIA",
    "XLB",
    "XLE",
    "XLF",
    "XLI",
    "XLK",
    "XLP",
    "XLU",
    "XLV",
    "XLY",
    "KRE",
    "IYT",
    "XME",
    "ITA",
    "SMH",
    "GLD",
    "GDX",
    "SLV",
    "DBA",
    "COPX",
    "URA",
    "UUP",
    "EFA",
    "EEM",
    "VNQ",
    "HYG",
    "TLT",
    "IEF",
    "SHY",
    "BIL",
)

BENCHMARK = "SPY"
CASH_PROXY = "BIL"
RISK_UNIVERSE: tuple[str, ...] = tuple(ticker for ticker in ETF_UNIVERSE if ticker != CASH_PROXY)
