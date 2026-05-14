---
name: kobserver
description: Manage a global market watchlist for US stocks, Hong Kong stocks, and crypto; render watchlist quotes or single-symbol candlestick charts as PNG images using a bundled Python CLI.
metadata: { "openclaw": { "requires": { "bins": ["uv"] }, "install": [ { "id": "uv", "kind": "brew", "formula": "uv", "bins": ["uv"], "label": "Install uv (brew)" } ] } }
---

# Kobserver

Use this skill when the user wants to manage a market watchlist, view current prices for all watched symbols, or generate a candlestick chart for one watched symbol.

Supported assets:

- US stocks through Yahoo-compatible public data via `yfinance`.
- Hong Kong stocks through Yahoo-compatible public data via `yfinance`.
- Crypto through Pyth public APIs.

The skill is API-key free. Extended-hours stock data is best-effort. Crypto symbols such as `BTC` normalize to `BTC/USD`.

## Commands

Run the bundled CLI from the skill directory:

```bash
cd {baseDir}/scripts
uv run python kobserver.py --json list
```

Add symbols:

```bash
cd {baseDir}/scripts
uv run python kobserver.py --json add AAPL --type us
uv run python kobserver.py --json add 0700 --type hk
uv run python kobserver.py --json add BTC --type crypto
```

Remove symbols:

```bash
cd {baseDir}/scripts
uv run python kobserver.py --json remove BTC
```

Render the watchlist quote image:

```bash
cd {baseDir}/scripts
uv run python kobserver.py --json quotes --output /tmp/kobserver-quotes.png
```

Render one candlestick chart:

```bash
cd {baseDir}/scripts
uv run python kobserver.py --json chart AAPL --output /tmp/kobserver-aapl.png
uv run python kobserver.py --json chart BTC --output /tmp/kobserver-btc.png
```

After rendering, return the generated PNG path to the user and display it inline when the client supports local image rendering.

## Behavior

- Watchlist data is stored at `~/.openclaw-data/kobserver/watchlist.json`.
- Quote PNG columns are `Symbol`, `Name`, `Price`, `Change`, `Session`, and `Note`.
- Quote PNGs do not show a `Source` column.
- Candlestick PNGs include a bottom time axis and a right-side price axis.
- If one quote fails, keep rendering the other rows.
- If chart data is unavailable, return the generated error PNG.

Read `references/data-sources.md` before changing provider behavior.
