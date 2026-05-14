import pytest

from kobserver_core.symbols import normalize_symbol, resolve_common_pyth_feed


def test_normalize_us_symbol():
    normalized = normalize_symbol("aapl", "us")
    assert normalized.type == "us"
    assert normalized.symbol == "AAPL"
    assert normalized.display == "AAPL"
    assert normalized.pyth_id is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0700", "0700.HK"),
        ("700", "0700.HK"),
        ("0700.HK", "0700.HK"),
    ],
)
def test_normalize_hk_symbol(raw, expected):
    normalized = normalize_symbol(raw, "hk")
    assert normalized.type == "hk"
    assert normalized.symbol == expected
    assert normalized.display == expected


@pytest.mark.parametrize("raw", ["BTC", "btc", "BTC/USD"])
def test_normalize_crypto_symbol(raw):
    normalized = normalize_symbol(raw, "crypto")
    assert normalized.type == "crypto"
    assert normalized.symbol == "BTC/USD"
    assert normalized.display == "BTC"
    assert normalized.pyth_id == "e62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43"


def test_resolve_unknown_common_feed_returns_none():
    assert resolve_common_pyth_feed("NOTREAL/USD") is None
