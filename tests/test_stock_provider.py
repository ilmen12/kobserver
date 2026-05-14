from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from kobserver_core.models import WatchlistItem
from kobserver_core.providers import StockProvider


class FakeTicker:
    def __init__(self, info, history_frame):
        self.info = info
        self._history_frame = history_frame

    def history(self, *args, **kwargs):
        return self._history_frame


class SequenceTicker:
    def __init__(self, frames):
        self.info = {}
        self._frames = list(frames)

    def history(self, *args, **kwargs):
        return self._frames.pop(0)


def test_stock_quote_prefers_premarket_when_available():
    frame = pd.DataFrame()
    ticker = FakeTicker(
        {
            "regularMarketPrice": 190.0,
            "regularMarketPreviousClose": 188.0,
            "preMarketPrice": 191.2,
            "shortName": "Apple",
        },
        frame,
    )
    provider = StockProvider(ticker_factory=lambda symbol: ticker)
    item = WatchlistItem(type="us", symbol="AAPL", display="AAPL", name="Apple")

    quote = provider.quote(item)

    assert quote.price == 191.2
    assert round(quote.change, 2) == 3.2
    assert round(quote.change_percent, 4) == 1.7021
    assert quote.session == "Pre"
    assert quote.note == "extended"


def test_stock_chart_converts_history_rows():
    index = pd.DatetimeIndex(
        [datetime(2026, 5, 14, 9, 30), datetime(2026, 5, 14, 9, 35)],
        tz=ZoneInfo("America/New_York"),
    )
    frame = pd.DataFrame(
        {
            "Open": [10.0, 11.0],
            "High": [11.0, 12.0],
            "Low": [9.5, 10.5],
            "Close": [10.8, 11.8],
            "Volume": [1000, 1200],
        },
        index=index,
    )
    ticker = FakeTicker({"shortName": "Test"}, frame)
    provider = StockProvider(ticker_factory=lambda symbol: ticker)
    item = WatchlistItem(type="us", symbol="TEST", display="TEST")

    chart = provider.chart(item, interval="5m", timezone_name="Asia/Shanghai")

    assert chart.source == "Yahoo"
    assert chart.interval == "5m"
    assert len(chart.candles) == 2
    assert chart.candles[0].volume == 1000


def test_stock_chart_fallback_keeps_only_latest_trading_day():
    empty = pd.DataFrame()
    index = pd.DatetimeIndex(
        [
            datetime(2026, 5, 13, 15, 55),
            datetime(2026, 5, 13, 16, 0),
            datetime(2026, 5, 14, 9, 30),
            datetime(2026, 5, 14, 9, 35),
        ],
        tz=ZoneInfo("America/New_York"),
    )
    fallback = pd.DataFrame(
        {
            "Open": [8.0, 8.5, 10.0, 11.0],
            "High": [9.0, 9.5, 11.0, 12.0],
            "Low": [7.5, 8.0, 9.5, 10.5],
            "Close": [8.8, 9.0, 10.8, 11.8],
            "Volume": [800, 900, 1000, 1200],
        },
        index=index,
    )
    ticker = SequenceTicker([empty, fallback])
    provider = StockProvider(ticker_factory=lambda symbol: ticker)
    item = WatchlistItem(type="us", symbol="TEST", display="TEST")

    chart = provider.chart(item, interval="5m", timezone_name="Asia/Shanghai")

    assert len(chart.candles) == 2
    assert [candle.open for candle in chart.candles] == [10.0, 11.0]
