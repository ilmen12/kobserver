# Kobserver Data Sources

Stocks use Finnhub REST APIs. Latest quotes come from `/quote`; candlesticks come from `/stock/candle`. Stock requests require `FINNHUB_API_KEY` or `FINNHUB_TOKEN` in the environment. Finnhub's quote endpoint does not provide separate pre-market and after-hours fields in the response used by Kobserver, so stock session labels are best-effort.

Crypto uses Pyth public APIs rather than CEX APIs. Latest prices come from Hermes `/v2/updates/price/latest` by feed ID. Candlesticks come from Pyth History `/v1/real_time/history` with TradingView-style OHLC arrays. Watchlist symbols are stored as pairs such as `BTC/USD`, but History API requests use Pyth TradingView symbols such as `Crypto.BTC/USD`.

The first version bundles common Pyth feed IDs for BTC/USD, ETH/USD, and SOL/USD. For unsupported crypto symbols, the CLI should return a clear unsupported-symbol message.
