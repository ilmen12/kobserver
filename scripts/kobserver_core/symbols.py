from __future__ import annotations

from kobserver_core.models import AssetType, NormalizedSymbol

COMMON_PYTH_FEEDS: dict[str, dict[str, str]] = {
    "BTC/USD": {
        "id": "e62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43",
        "name": "Bitcoin",
    },
    "ETH/USD": {
        "id": "ff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace",
        "name": "Ethereum",
    },
    "SOL/USD": {
        "id": "ef0d8b6fda2ceba41da15d4095d1da392a0d2f8ed0c6c7bc0f4cfac8c280b56d",
        "name": "Solana",
    },
}


def resolve_common_pyth_feed(symbol: str) -> str | None:
    record = COMMON_PYTH_FEEDS.get(symbol.upper())
    if record is None:
        return None
    return record["id"]


def normalize_symbol(raw: str, asset_type: AssetType) -> NormalizedSymbol:
    cleaned = raw.strip().upper()
    if not cleaned:
        raise ValueError("symbol cannot be empty")

    if asset_type == "us":
        return NormalizedSymbol(type="us", symbol=cleaned, display=cleaned)

    if asset_type == "hk":
        base = cleaned.removesuffix(".HK")
        if not base.isdigit():
            raise ValueError(f"HK symbol must be numeric or end in .HK: {raw}")
        symbol = f"{int(base):04d}.HK"
        return NormalizedSymbol(type="hk", symbol=symbol, display=symbol)

    if asset_type == "crypto":
        pair = cleaned if "/" in cleaned else f"{cleaned}/USD"
        base = pair.split("/", 1)[0]
        return NormalizedSymbol(
            type="crypto",
            symbol=pair,
            display=base,
            pyth_id=resolve_common_pyth_feed(pair),
        )

    raise ValueError(f"unsupported asset type: {asset_type}")


def parse_symbol_token(token: str) -> NormalizedSymbol:
    cleaned = token.strip()
    if ":" not in cleaned:
        raise ValueError(f"symbol token must include a market prefix like us:AAPL, hk:0700, or crypto:BTC: {token}")
    prefix, raw_symbol = cleaned.split(":", 1)
    asset_type = prefix.strip().lower()
    if asset_type not in {"us", "hk", "crypto"}:
        raise ValueError(f"unsupported market prefix: {prefix}")
    return normalize_symbol(raw_symbol, asset_type)  # type: ignore[arg-type]
