import json

from kobserver_core.models import WatchlistItem
from kobserver_core.watchlist import WatchlistStore


def test_add_list_and_deduplicate(tmp_path):
    store = WatchlistStore(tmp_path)
    first = WatchlistItem(type="us", symbol="AAPL", display="AAPL", name="Apple")
    second = WatchlistItem(type="us", symbol="AAPL", display="AAPL", name="Apple")

    assert store.add(first) is True
    assert store.add(second) is False

    items = store.list_items()
    assert len(items) == 1
    assert items[0].symbol == "AAPL"


def test_remove_by_display_or_symbol(tmp_path):
    store = WatchlistStore(tmp_path)
    store.add(WatchlistItem(type="crypto", symbol="BTC/USD", display="BTC", pyth_id="feed"))

    removed = store.remove("BTC")

    assert removed == [("crypto", "BTC/USD")]
    assert store.list_items() == []


def test_preserves_unknown_fields(tmp_path):
    path = tmp_path / "watchlist.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "items": [
                    {
                        "type": "us",
                        "symbol": "MSFT",
                        "display": "MSFT",
                        "custom": "kept",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    store = WatchlistStore(tmp_path)

    item = store.list_items()[0]

    assert item.extra == {"custom": "kept"}
