from datetime import datetime, timezone

import pytest

from kobserver_core.models import WatchlistItem
from kobserver_core.providers import StockProvider


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        return FakeResponse(self.payloads.pop(0))


def test_stock_quote_uses_finnhub_quote_endpoint():
    regular_timestamp = int(datetime(2026, 5, 14, 14, 30, tzinfo=timezone.utc).timestamp())
    session = FakeSession(
        [
            {
                "c": 191.2,
                "d": 3.2,
                "dp": 1.7021,
                "pc": 188.0,
                "t": regular_timestamp,
            }
        ]
    )
    provider = StockProvider(token="test-token", session=session)
    item = WatchlistItem(type="us", symbol="AAPL", display="AAPL", name="Apple")

    quote = provider.quote(item)

    assert session.calls[0]["url"].endswith("/quote")
    assert session.calls[0]["params"] == {"symbol": "AAPL", "token": "test-token"}
    assert quote.price == 191.2
    assert quote.change == 3.2
    assert quote.change_percent == 1.7021
    assert quote.session == "Regular"
    assert quote.note == ""
    assert quote.timestamp == datetime.fromtimestamp(regular_timestamp, timezone.utc)
    assert quote.source == "Finnhub"


def test_stock_quote_requires_finnhub_api_key(monkeypatch):
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    monkeypatch.delenv("FINNHUB_TOKEN", raising=False)
    provider = StockProvider(session=FakeSession([]))
    item = WatchlistItem(type="us", symbol="AAPL", display="AAPL")

    with pytest.raises(ValueError, match="FINNHUB_API_KEY"):
        provider.quote(item)


def test_stock_quote_rejects_empty_finnhub_quote_payload():
    session = FakeSession([{"c": 0, "d": 0, "dp": 0, "pc": 0, "t": 0}])
    provider = StockProvider(token="test-token", session=session)
    item = WatchlistItem(type="us", symbol="MISSING", display="MISSING")

    with pytest.raises(ValueError, match="No usable Finnhub quote"):
        provider.quote(item)


def test_stock_quote_labels_us_premarket_from_finnhub_timestamp():
    premarket_timestamp = int(datetime(2026, 5, 14, 12, 30, tzinfo=timezone.utc).timestamp())
    session = FakeSession(
        [
            {
                "c": 191.2,
                "d": 3.2,
                "dp": 1.7021,
                "pc": 188.0,
                "t": premarket_timestamp,
            }
        ]
    )
    provider = StockProvider(token="test-token", session=session)
    item = WatchlistItem(type="us", symbol="AAPL", display="AAPL", name="Apple")

    quote = provider.quote(item)

    assert quote.session == "Pre"
    assert quote.note == "extended"


def test_stock_chart_converts_finnhub_candles():
    timestamps = [
        int(datetime(2026, 5, 14, 13, 30, tzinfo=timezone.utc).timestamp()),
        int(datetime(2026, 5, 14, 13, 35, tzinfo=timezone.utc).timestamp()),
    ]
    session = FakeSession(
        [
            {
                "s": "ok",
                "t": timestamps,
                "o": [10.0, 11.0],
                "h": [11.0, 12.0],
                "l": [9.5, 10.5],
                "c": [10.8, 11.8],
                "v": [1000, 1200],
            }
        ]
    )
    provider = StockProvider(
        token="test-token",
        session=session,
        now_fn=lambda: datetime(2026, 5, 14, 16, 0, tzinfo=timezone.utc),
    )
    item = WatchlistItem(type="us", symbol="TEST", display="TEST")

    chart = provider.chart(item, interval="5m", timezone_name="Asia/Shanghai")

    assert session.calls[0]["url"].endswith("/stock/candle")
    assert session.calls[0]["params"]["symbol"] == "TEST"
    assert session.calls[0]["params"]["resolution"] == "5"
    assert session.calls[0]["params"]["token"] == "test-token"
    assert chart.source == "Finnhub"
    assert chart.interval == "5m"
    assert len(chart.candles) == 2
    assert chart.candles[0].volume == 1000


def test_stock_chart_keeps_only_latest_trading_day():
    timestamps = [
        int(datetime(2026, 5, 13, 13, 55, tzinfo=timezone.utc).timestamp()),
        int(datetime(2026, 5, 13, 14, 0, tzinfo=timezone.utc).timestamp()),
        int(datetime(2026, 5, 14, 13, 30, tzinfo=timezone.utc).timestamp()),
        int(datetime(2026, 5, 14, 13, 35, tzinfo=timezone.utc).timestamp()),
    ]
    session = FakeSession(
        [
            {
                "s": "ok",
                "t": timestamps,
                "o": [8.0, 8.5, 10.0, 11.0],
                "h": [9.0, 9.5, 11.0, 12.0],
                "l": [7.5, 8.0, 9.5, 10.5],
                "c": [8.8, 9.0, 10.8, 11.8],
                "v": [800, 900, 1000, 1200],
            }
        ]
    )
    provider = StockProvider(
        token="test-token",
        session=session,
        now_fn=lambda: datetime(2026, 5, 14, 16, 0, tzinfo=timezone.utc),
    )
    item = WatchlistItem(type="us", symbol="TEST", display="TEST")

    chart = provider.chart(item, interval="5m", timezone_name="Asia/Shanghai")

    assert len(chart.candles) == 2
    assert [candle.open for candle in chart.candles] == [10.0, 11.0]
