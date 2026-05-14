# Kobserver Skill Design

Date: 2026-05-14
Status: approved design draft pending user review

## Summary

`kobserver` is an OpenClaw-installable skill for managing a global market watchlist and rendering market data as images. It supports US stocks, Hong Kong stocks, and crypto. It is designed to work without API keys.

The skill bundles a Python CLI that OpenClaw agents call for deterministic behavior:

- Manage a global watchlist: add, remove, list, and view items.
- Render a watchlist quote overview as a PNG.
- Render a single-symbol candlestick chart as a PNG.

Data sources:

- US stocks and Hong Kong stocks: `yfinance`, using Yahoo-compatible public data.
- Crypto: Pyth public APIs, avoiding Binance, OKX, and other CEX APIs.

## OpenClaw Skill Shape

The installable skill name is `kobserver`.

OpenClaw loads AgentSkills-compatible skill folders with a required `SKILL.md` file. The project should be installable as a folder named `kobserver`, with `SKILL.md` at the folder root and bundled scripts under `scripts/`.

Planned structure:

```text
kobserver/
  SKILL.md
  agents/openai.yaml
  scripts/
    kobserver.py
    pyproject.toml
  references/
    data-sources.md
  tests/
```

The `SKILL.md` frontmatter should:

- Use `name: kobserver`.
- Describe the watchlist, quote rendering, and K-line chart behavior.
- Declare `uv` as a required binary through OpenClaw metadata.
- Include installer metadata for `uv` where appropriate.
- Instruct the agent to call `{baseDir}/scripts/kobserver.py` through `uv run`.

## User Data

Watchlist data is global per user, not per workspace.

Path:

```text
~/.openclaw-data/kobserver/watchlist.json
```

Schema:

```json
{
  "version": 1,
  "items": [
    {
      "type": "us",
      "symbol": "AAPL",
      "display": "AAPL",
      "name": "Apple Inc.",
      "created_at": "2026-05-14T14:30:00+08:00"
    },
    {
      "type": "hk",
      "symbol": "0700.HK",
      "display": "0700.HK",
      "name": "Tencent",
      "created_at": "2026-05-14T14:31:00+08:00"
    },
    {
      "type": "crypto",
      "symbol": "BTC/USD",
      "display": "BTC",
      "pyth_id": "e62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43",
      "name": "Bitcoin",
      "created_at": "2026-05-14T14:32:00+08:00"
    }
  ]
}
```

Rules:

- Deduplicate by `type + symbol`.
- Preserve unknown fields when loading and saving future versions.
- Write changes atomically using a temporary file and rename.
- Create the data directory on first use.
- Default timezone for displayed timestamps is `Asia/Shanghai`.

## CLI Interface

The CLI command name is `kobserver`.

Core commands:

```bash
kobserver add AAPL --type us
kobserver add 0700.HK --type hk
kobserver add BTC --type crypto
kobserver remove BTC
kobserver list
kobserver quotes --output /tmp/kobserver-quotes.png
kobserver chart AAPL --output /tmp/kobserver-aapl.png
kobserver chart BTC --output /tmp/kobserver-btc.png
```

Command behavior:

- `add` normalizes the symbol, resolves metadata where possible, and writes to the global watchlist.
- `remove` accepts either the display symbol or normalized symbol.
- `list` prints a human-readable table and also supports JSON output.
- `quotes` fetches all watchlist prices and renders a PNG.
- `chart` renders one symbol's candlestick chart.

Recommended options:

```bash
--json                  print structured JSON summary
--output PATH           write PNG to this path
--data-dir PATH         override global data dir for tests
--timezone TZ           override display timezone, default Asia/Shanghai
--interval 5m           chart interval where supported
--width 1600
--height 900
```

## Symbol Normalization

US stocks:

- Input: `aapl`, `AAPL`
- Stored symbol: `AAPL`
- Display: `AAPL`
- Provider: yfinance

Hong Kong stocks:

- Input: `0700`, `700`, `0700.HK`
- Stored symbol: `0700.HK`
- Display: `0700.HK`
- Provider: yfinance

Crypto:

- Input: `BTC`, `btc`, `BTC/USD`
- Stored symbol: `BTC/USD`
- Display: `BTC`
- Provider: Pyth

Crypto feed resolution:

- First use a bundled common-feed registry for symbols such as `BTC/USD`, `ETH/USD`, and `SOL/USD`.
- If the symbol is not bundled, query Pyth symbol endpoints to search or resolve the symbol.
- If no Pyth feed is found, return a clear unsupported-symbol error.

## Data Providers

### Stock Provider

The stock provider uses `yfinance`.

Required outputs:

- Current or latest available price.
- Absolute and percent change versus the relevant previous close.
- Session label: `Regular`, `Pre`, `After`, `Closed`, or `Unavailable`.
- Optional note: `extended`, `last close`, `delayed`, or an error summary.
- Intraday candles for the chart.

Extended-hours behavior is best-effort:

- If Yahoo-compatible data exposes pre-market or after-hours values, show them.
- If extended-hours data is missing, fall back to regular/latest close and mark the note.
- Overnight trading is shown only if exposed by the public data source.

### Crypto Provider

The crypto provider uses Pyth public APIs.

Latest price:

- Use Hermes `/v2/updates/price/latest` with one or more feed IDs.
- Parse the `parsed[].price` object.
- Convert integer price using `price * 10^expo`.
- Use `publish_time` as the quote timestamp.

Historical candles:

- Use Pyth History API at `https://pyth.dourolabs.app/v1`.
- Use `/{channel}/history` for TradingView-style OHLC data.
- Default channel: `real_time`.
- Default crypto chart range: last 24 hours.
- Default resolution: `5`.
- If there is not enough data, retry with `15`, then `60`.

Pyth History returns aligned arrays for timestamp, open, high, low, close, and optionally volume. Volume should be rendered only if present.

## Quote PNG Design

The quote overview image is optimized for chat display.

Title:

```text
Kobserver Watchlist
```

Subtitle:

```text
<render timestamp> Asia/Shanghai
```

Columns:

- `Symbol`
- `Name`
- `Price`
- `Change`
- `Session`
- `Note`

No `Source` column is shown in the image. Source details remain available in JSON metadata.

Rendering rules:

- Positive changes are green.
- Negative changes are red.
- Zero or missing changes are neutral.
- Failed symbols still render a row with `Unavailable` and a short note.
- Long names and notes are truncated gracefully.
- The image should stay readable for watchlists from 1 to about 40 items.
- If the watchlist is very large, paginate or reduce row height rather than making unreadable text.

## Candlestick PNG Design

The chart image must include readable axes.

Required elements:

- Title with symbol and range.
- Subtitle with interval, latest price, and percent change when available.
- Candlestick chart.
- Right-side Y-axis price scale.
- Bottom X-axis time scale in the display timezone.
- Grid lines.
- Volume subplot when volume is available.
- Data-source details in JSON metadata, not as a dominant chart label.

Range rules:

- US/HK stock: use the current trading day if intraday data exists.
- US/HK stock: if today has no valid session data, fall back to the previous trading day.
- Crypto: use the most recent 24 hours.

Failure behavior:

- If all chart data attempts fail, generate an error PNG explaining the symbol and the reason.
- The CLI should still return structured JSON containing the error.

## Error Handling

Errors are isolated per symbol.

For `quotes`:

- Fetch all watchlist symbols.
- If one symbol fails, keep rendering the other rows.
- Render the failed row with `Unavailable`.
- Return a JSON summary with `ok`, `failed`, and per-symbol error details.

For `chart`:

- Retry provider-specific fallbacks.
- If no usable data remains, render an error image.
- Exit nonzero only for CLI misuse, filesystem failures, or renderer failures that prevent any output.

Network and provider failures should mention the provider and operation but avoid noisy stack traces in normal output.

## Dependencies

Use `uv` to manage Python execution and dependencies.

Planned Python packages:

- `requests`
- `yfinance`
- `matplotlib`
- `mplfinance`
- `pillow`
- `pydantic` or standard-library `dataclasses`

Prefer deterministic script entry points over relying on the agent to write ad hoc query or chart code.

## Testing

Automated tests:

- Watchlist add, remove, list, deduplication, and global path behavior.
- Symbol normalization for US, HK, and crypto.
- Crypto feed-id lookup from bundled registry.
- Provider model parsing with mocked HTTP/yfinance responses.
- Renderer creates a non-empty PNG.
- Error PNG rendering.
- JSON output shape.

Manual smoke tests:

- Add `AAPL`, `0700.HK`, and `BTC`.
- Render a quote overview.
- Render stock chart.
- Render crypto chart.
- Confirm output images have readable axes and no `Source` column in quotes.

Automated tests should not depend on live APIs. Live API tests are optional smoke checks.

## Non-Goals For First Version

- API-key configuration.
- Paid market data integrations.
- Portfolio positions, P/L, cost basis, or alerts.
- User-configurable provider routing.
- Full support for all global exchanges.
- Guaranteed overnight-session support for stocks.
- CEX API integration for crypto.

## References

- OpenClaw skill folders and `SKILL.md`: https://raw.githubusercontent.com/openclaw/openclaw/main/docs/tools/skills.md
- Pyth latest price updates: https://docs.pyth.network/price-feeds/core/fetch-price-updates
- Pyth History API: https://docs.pyth.network/price-feeds/pro/api/history
