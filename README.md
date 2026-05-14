# Kobserver

`kobserver` is an OpenClaw-installable skill for managing a global market watchlist and rendering market data as images.

It supports:

- US stocks through Yahoo-compatible public data via `yfinance`
- Hong Kong stocks through Yahoo-compatible public data via `yfinance`
- Crypto through Pyth public APIs

The skill is designed to work without API keys. Stock extended-hours data is best-effort. Crypto data avoids Binance, OKX, and other CEX APIs.

## Features

- Manage a global watchlist stored outside the skill folder.
- Add, remove, and list US stocks, Hong Kong stocks, and crypto symbols.
- Render the whole watchlist as a quote table PNG.
- Render a single-symbol candlestick chart PNG.
- Show stock pre-market and after-hours prices when public data exposes them.
- Show crypto prices and recent 24h candles through Pyth.
- Keep rendering partial results when one watchlist item fails.
- Generate an error PNG for unavailable chart data instead of silently failing.

## Project Layout

```text
.
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   └── data-sources.md
├── scripts/
│   ├── kobserver.py
│   ├── pyproject.toml
│   └── kobserver_core/
└── tests/
```

## Requirements

- OpenClaw with skill support
- `uv`
- Python 3.11 or newer

On macOS, install `uv` with:

```bash
brew install uv
```

The Python dependencies are declared in `scripts/pyproject.toml` and are installed automatically by `uv run`.

## Installation

### Install As An OpenClaw Skill

Place or clone this folder into the location where your OpenClaw installation discovers skills. The folder name should be:

```text
kobserver
```

The required skill entrypoint is:

```text
kobserver/SKILL.md
```

`SKILL.md` declares `uv` as the required runtime tool and instructs OpenClaw agents to run the bundled CLI from:

```text
{baseDir}/scripts/kobserver.py
```

After installation, ask OpenClaw for tasks such as:

```text
Use $kobserver to add crypto:BTC to my watchlist.
Use $kobserver to replace my watchlist with us:AAPL crypto:BTC hk:0700.
Use $kobserver to show my watchlist as an image.
Use $kobserver to render a K-line chart for us:AAPL.
```

### Use The CLI Directly

From the project root:

```bash
cd scripts
uv run python kobserver.py --json list
```

## Watchlist Storage

By default, watchlist data is stored globally at:

```text
~/.openclaw-data/kobserver/watchlist.json
```

This means the watchlist is not tied to a single workspace and should survive skill updates.

For tests or temporary runs, override the data directory:

```bash
cd scripts
uv run python kobserver.py --data-dir /tmp/kobserver-demo --json list
```

## Symbol Formats

The recommended watchlist token format is:

```text
<market>:<symbol>
```

Supported market prefixes are `us`, `hk`, and `crypto`. Prefixes let mixed watchlists preserve the exact input order.

US stocks:

```bash
uv run python kobserver.py --json add us:AAPL
```

Hong Kong stocks:

```bash
uv run python kobserver.py --json add hk:0700
uv run python kobserver.py --json add hk:0700.HK
```

Both `0700` and `700` normalize to `0700.HK`.

Crypto:

```bash
uv run python kobserver.py --json add crypto:BTC
uv run python kobserver.py --json add crypto:BTC/USD
```

`crypto:BTC` normalizes to `BTC/USD`. Common bundled Pyth feeds include `BTC/USD`, `ETH/USD`, and `SOL/USD`.

Legacy `--type` usage is still supported for single-symbol commands, for example `add AAPL --type us`.

## Usage

Run all examples from `scripts/`.

### Add Symbols

```bash
uv run python kobserver.py --json add us:AAPL
uv run python kobserver.py --json add hk:0700
uv run python kobserver.py --json add crypto:BTC
```

### Replace The Full Watchlist

```bash
uv run python kobserver.py --json replace us:AAPL crypto:BTC hk:0700 us:MSFT crypto:ETH
```

`replace` overwrites the current watchlist and preserves the mixed input order. All symbols passed to `replace` must include a market prefix.

### List The Watchlist

```bash
uv run python kobserver.py --json list
```

### Remove A Symbol

```bash
uv run python kobserver.py --json remove crypto:BTC
uv run python kobserver.py --json remove us:AAPL
```

### Render Watchlist Quotes

```bash
uv run python kobserver.py --json quotes --output /tmp/kobserver-quotes.png
```

The quote image columns are:

- `Symbol`
- `Name`
- `Price`
- `Change`
- `Session`
- `Note`

The image intentionally does not show a `Source` column. Source details remain in the JSON command output.

### Render A Candlestick Chart

```bash
uv run python kobserver.py --json chart us:AAPL --output /tmp/kobserver-aapl.png
uv run python kobserver.py --json chart crypto:BTC --output /tmp/kobserver-btc.png
```

Chart behavior:

- US/HK stocks use current-day intraday data when available.
- If current-day stock data is unavailable, the chart falls back to the latest trading day.
- Crypto charts use the most recent 24 hours.
- Charts include a bottom time axis and a right-side price axis.
- Volume is shown only when usable volume data is available.

## Useful Options

```bash
--json                 Print structured JSON output.
--data-dir PATH        Override the global watchlist data directory.
--timezone TZ          Override display timezone. Default: Asia/Shanghai.
--output PATH          PNG output path for quotes/chart commands.
--interval 5m          Chart interval where supported.
--width 1600           Output image width.
--height 900           Output image height.
```

## Data Source Notes

Stocks use `yfinance`, which depends on Yahoo-compatible public data. Pre-market, after-hours, and overnight fields are best-effort. When the provider omits extended-hours values, Kobserver falls back to regular or latest close data and marks the note.

Crypto uses Pyth public APIs:

- Latest prices use Hermes `/v2/updates/price/latest`.
- Candlesticks use Pyth History `/v1/real_time/history`.
- Stored crypto symbols use pairs such as `BTC/USD`.
- Pyth History requests use TradingView symbols such as `Crypto.BTC/USD`.

See `references/data-sources.md` before changing provider behavior.

## Testing

Run the full test suite:

```bash
cd scripts
uv run --with pytest pytest ../tests -v
```

Run a local CLI smoke test with isolated data:

```bash
cd scripts
tmp_dir="$(mktemp -d)"
uv run python kobserver.py --data-dir "$tmp_dir" --json replace us:AAPL hk:0700 crypto:BTC
uv run python kobserver.py --data-dir "$tmp_dir" --json list
```

Run a live Pyth smoke test:

```bash
cd scripts
tmp_dir="$(mktemp -d)"
uv run python kobserver.py --data-dir "$tmp_dir" --json add crypto:BTC
uv run python kobserver.py --data-dir "$tmp_dir" --json quotes --output /tmp/kobserver-quotes.png
uv run python kobserver.py --data-dir "$tmp_dir" --json chart crypto:BTC --output /tmp/kobserver-btc.png
```

## Limitations

- No API-key provider configuration in the first version.
- No portfolio positions, cost basis, P/L, alerts, or notifications.
- Stock overnight trading is displayed only if public Yahoo-compatible data exposes it.
- Pyth crypto support depends on available Pyth symbols and feeds.
- First-version bundled Pyth feed IDs cover only common assets.

## Development Notes

- Keep provider behavior deterministic and covered by tests.
- Automated tests should not depend on live APIs.
- Prefer mocked provider tests plus a small optional live smoke test.
- Do not add CEX API dependencies unless the network policy and product requirement change.
