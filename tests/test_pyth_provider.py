from datetime import datetime, timezone

from kobserver_core.models import WatchlistItem
from kobserver_core.providers import PythProvider


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.urls = []

    def get(self, url, params=None, timeout=None):
        self.urls.append((url, params, timeout))
        return FakeResponse(self.payloads.pop(0))


def test_latest_quote_parses_pyth_exponent():
    item = WatchlistItem(
        type="crypto",
        symbol="BTC/USD",
        display="BTC",
        pyth_id="feed",
        name="Bitcoin",
    )
    session = FakeSession(
        [
            {
                "parsed": [
                    {
                        "id": "feed",
                        "price": {
                            "price": "6412000000000",
                            "expo": -8,
                            "publish_time": 1778742000,
                        },
                    }
                ]
            }
        ]
    )
    provider = PythProvider(session=session)

    quote = provider.quote(item)

    assert quote.price == 64120.0
    assert quote.session == "24/7"
    assert quote.source == "Pyth"
    assert quote.timestamp == datetime.fromtimestamp(1778742000, timezone.utc)


def test_history_parses_aligned_ohlc_arrays():
    item = WatchlistItem(type="crypto", symbol="BTC/USD", display="BTC", pyth_id="feed")
    session = FakeSession(
        [
            {
                "s": "ok",
                "t": [1778738400, 1778738700],
                "o": [64000.0, 64100.0],
                "h": [64200.0, 64250.0],
                "l": [63900.0, 64050.0],
                "c": [64100.0, 64200.0],
            }
        ]
    )
    provider = PythProvider(session=session)

    chart = provider.chart(item, interval="5m", timezone_name="Asia/Shanghai")

    assert chart.source == "Pyth"
    assert chart.interval == "5m"
    assert len(chart.candles) == 2
    assert chart.candles[0].open == 64000.0
    assert chart.candles[1].close == 64200.0


def test_history_uses_pyth_tradingview_symbol_prefix():
    item = WatchlistItem(type="crypto", symbol="BTC/USD", display="BTC", pyth_id="feed")
    session = FakeSession(
        [
            {
                "s": "ok",
                "t": [1778738400, 1778738700],
                "o": [64000.0, 64100.0],
                "h": [64200.0, 64250.0],
                "l": [63900.0, 64050.0],
                "c": [64100.0, 64200.0],
            }
        ]
    )
    provider = PythProvider(session=session)

    provider.chart(item, interval="5m", timezone_name="Asia/Shanghai")

    assert session.urls[0][1]["symbol"] == "Crypto.BTC/USD"
