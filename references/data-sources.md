# Kobserver Data Sources

Stocks use `yfinance`, which depends on Yahoo-compatible public data. Pre-market, after-hours, and overnight fields are best-effort; when the provider omits them, use regular or latest close data and mark the quote note.

Crypto uses Pyth public APIs rather than CEX APIs. Latest prices come from Hermes `/v2/updates/price/latest` by feed ID. Candlesticks come from Pyth History `/v1/real_time/history` with TradingView-style OHLC arrays. Watchlist symbols are stored as pairs such as `BTC/USD`, but History API requests use Pyth TradingView symbols such as `Crypto.BTC/USD`.

The first version bundles common Pyth feed IDs for BTC/USD, ETH/USD, and SOL/USD. For unsupported crypto symbols, the CLI should return a clear unsupported-symbol message.
