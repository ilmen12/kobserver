# Kobserver Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `kobserver` OpenClaw skill: a global watchlist manager that renders US/HK stock and Pyth crypto quotes or candlestick charts as PNG images.

**Architecture:** The skill root is this repository. `SKILL.md` teaches OpenClaw when and how to call a deterministic Python CLI. The CLI lives in `scripts/kobserver.py` and delegates to focused modules under `scripts/kobserver_core/` for models, watchlist storage, providers, rendering, and command handling.

**Tech Stack:** Python 3.11+, `uv`, `pytest`, `requests`, `yfinance`, `matplotlib`, `mplfinance`, `pillow`, standard-library `argparse`, `dataclasses`, `json`, `zoneinfo`, and `unittest.mock`.

---

## File Structure

- Create `SKILL.md`: OpenClaw skill instructions, dependency gates, CLI usage patterns.
- Create `agents/openai.yaml`: UI metadata for the skill.
- Create `scripts/pyproject.toml`: Python dependency and pytest config for the bundled CLI.
- Create `scripts/kobserver.py`: executable CLI wrapper.
- Create `scripts/kobserver_core/__init__.py`: package marker and version.
- Create `scripts/kobserver_core/models.py`: dataclasses for watchlist items, quotes, candles, and command results.
- Create `scripts/kobserver_core/symbols.py`: symbol normalization and Pyth common-feed registry.
- Create `scripts/kobserver_core/watchlist.py`: global watchlist load/save/add/remove/list behavior.
- Create `scripts/kobserver_core/providers.py`: yfinance stock provider and Pyth crypto provider.
- Create `scripts/kobserver_core/rendering.py`: quote table PNG, candlestick PNG, and error PNG rendering.
- Create `scripts/kobserver_core/cli.py`: argument parsing and command orchestration.
- Create `references/data-sources.md`: concise source behavior notes for future agents.
- Create tests under `tests/` mirroring the Python modules.

## Task 1: Python Project Scaffold

**Files:**
- Create: `scripts/pyproject.toml`
- Create: `scripts/kobserver.py`
- Create: `scripts/kobserver_core/__init__.py`
- Create: `tests/test_cli_smoke.py`

- [ ] **Step 1: Write the failing smoke test**

Create `tests/test_cli_smoke.py`:

```python
from kobserver_core.cli import build_parser


def test_parser_has_expected_subcommands():
    parser = build_parser()
    subparsers = [
        action
        for action in parser._actions
        if action.__class__.__name__ == "_SubParsersAction"
    ]
    assert len(subparsers) == 1
    assert {"add", "remove", "list", "quotes", "chart"} <= set(subparsers[0].choices)
```

- [ ] **Step 2: Run the test to verify it fails**

Run from the repository root:

```bash
cd scripts && uv run --with pytest pytest ../tests/test_cli_smoke.py -v
```

Expected: fail with `ModuleNotFoundError: No module named 'kobserver_core'`.

- [ ] **Step 3: Add the scaffold**

Create `scripts/pyproject.toml`:

```toml
[project]
name = "kobserver"
version = "0.1.0"
description = "OpenClaw skill CLI for market watchlists and chart rendering"
requires-python = ">=3.11"
dependencies = [
  "matplotlib>=3.8",
  "mplfinance>=0.12.10b0",
  "pillow>=10",
  "requests>=2.31",
  "yfinance>=0.2.40"
]

[project.optional-dependencies]
test = [
  "pytest>=8"
]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["../tests"]
```

Create `scripts/kobserver_core/__init__.py`:

```python
"""Core implementation for the kobserver OpenClaw skill."""

__version__ = "0.1.0"
```

Create `scripts/kobserver.py`:

```python
#!/usr/bin/env python3
from kobserver_core.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
```

Create `scripts/kobserver_core/cli.py`:

```python
from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kobserver",
        description="Manage a market watchlist and render quote or candlestick PNGs.",
    )
    parser.add_argument("--data-dir", help="Override the global data directory.")
    parser.add_argument("--timezone", default="Asia/Shanghai")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    add = subparsers.add_parser("add", help="Add a symbol to the watchlist.")
    add.add_argument("symbol")
    add.add_argument("--type", choices=["us", "hk", "crypto"], required=True)
    add.add_argument("--name")

    remove = subparsers.add_parser("remove", help="Remove a symbol from the watchlist.")
    remove.add_argument("symbol")
    remove.add_argument("--type", choices=["us", "hk", "crypto"])

    subparsers.add_parser("list", help="List watchlist items.")

    quotes = subparsers.add_parser("quotes", help="Render the watchlist quote PNG.")
    quotes.add_argument("--output", required=True)
    quotes.add_argument("--width", type=int, default=1600)
    quotes.add_argument("--height", type=int, default=900)

    chart = subparsers.add_parser("chart", help="Render a candlestick PNG for one symbol.")
    chart.add_argument("symbol")
    chart.add_argument("--type", choices=["us", "hk", "crypto"])
    chart.add_argument("--output", required=True)
    chart.add_argument("--interval", default="5m")
    chart.add_argument("--width", type=int, default=1600)
    chart.add_argument("--height", type=int, default=900)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    parser.print_help()
    return 0
```

- [ ] **Step 4: Run the smoke test**

```bash
cd scripts && uv run --with pytest pytest ../tests/test_cli_smoke.py -v
```

Expected: pass.

- [ ] **Step 5: Commit if this is a Git repository**

```bash
git status --short
git add scripts/pyproject.toml scripts/kobserver.py scripts/kobserver_core/__init__.py scripts/kobserver_core/cli.py tests/test_cli_smoke.py
git commit -m "chore: scaffold kobserver cli"
```

If `git status` reports this is not a Git repository, skip the commit and continue.

## Task 2: Models And Symbol Normalization

**Files:**
- Create: `scripts/kobserver_core/models.py`
- Create: `scripts/kobserver_core/symbols.py`
- Create: `tests/test_symbols.py`

- [ ] **Step 1: Write the failing symbol tests**

Create `tests/test_symbols.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd scripts && uv run --with pytest pytest ../tests/test_symbols.py -v
```

Expected: fail with `ModuleNotFoundError` or missing function errors.

- [ ] **Step 3: Add domain models**

Create `scripts/kobserver_core/models.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

AssetType = Literal["us", "hk", "crypto"]
SessionLabel = Literal["Regular", "Pre", "After", "Closed", "24/7", "Unavailable"]


@dataclass(slots=True)
class NormalizedSymbol:
    type: AssetType
    symbol: str
    display: str
    pyth_id: str | None = None


@dataclass(slots=True)
class WatchlistItem:
    type: AssetType
    symbol: str
    display: str
    name: str | None = None
    created_at: str | None = None
    pyth_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def key(self) -> tuple[str, str]:
        return (self.type, self.symbol)


@dataclass(slots=True)
class Quote:
    item: WatchlistItem
    price: float | None
    change: float | None
    change_percent: float | None
    session: SessionLabel
    note: str = ""
    timestamp: datetime | None = None
    source: str = ""
    error: str | None = None


@dataclass(slots=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None


@dataclass(slots=True)
class ChartData:
    item: WatchlistItem
    candles: list[Candle]
    interval: str
    range_label: str
    source: str
    note: str = ""
```

- [ ] **Step 4: Add symbol normalization**

Create `scripts/kobserver_core/symbols.py`:

```python
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
```

- [ ] **Step 5: Run the symbol tests**

```bash
cd scripts && uv run --with pytest pytest ../tests/test_symbols.py -v
```

Expected: pass.

- [ ] **Step 6: Commit if this is a Git repository**

```bash
git status --short
git add scripts/kobserver_core/models.py scripts/kobserver_core/symbols.py tests/test_symbols.py
git commit -m "feat: add symbol normalization"
```

If `git status` reports this is not a Git repository, skip the commit and continue.

## Task 3: Watchlist Storage

**Files:**
- Create: `scripts/kobserver_core/watchlist.py`
- Create: `tests/test_watchlist.py`

- [ ] **Step 1: Write the failing watchlist tests**

Create `tests/test_watchlist.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd scripts && uv run --with pytest pytest ../tests/test_watchlist.py -v
```

Expected: fail with missing `WatchlistStore`.

- [ ] **Step 3: Implement watchlist storage**

Create `scripts/kobserver_core/watchlist.py`:

```python
from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from kobserver_core.models import WatchlistItem

DEFAULT_DATA_DIR = Path.home() / ".openclaw-data" / "kobserver"
KNOWN_FIELDS = {"type", "symbol", "display", "name", "created_at", "pyth_id"}


def default_data_dir() -> Path:
    return DEFAULT_DATA_DIR


class WatchlistStore:
    def __init__(self, data_dir: str | Path | None = None, timezone: str = "Asia/Shanghai") -> None:
        self.data_dir = Path(data_dir) if data_dir is not None else default_data_dir()
        self.path = self.data_dir / "watchlist.json"
        self.timezone = timezone

    def list_items(self) -> list[WatchlistItem]:
        payload = self._load_payload()
        return [self._item_from_dict(record) for record in payload.get("items", [])]

    def add(self, item: WatchlistItem) -> bool:
        items = self.list_items()
        if any(existing.key() == item.key() for existing in items):
            return False
        if item.created_at is None:
            item.created_at = datetime.now(ZoneInfo(self.timezone)).isoformat(timespec="seconds")
        items.append(item)
        self._save_items(items)
        return True

    def remove(self, symbol: str, asset_type: str | None = None) -> list[tuple[str, str]]:
        needle = symbol.strip().upper()
        kept: list[WatchlistItem] = []
        removed: list[tuple[str, str]] = []
        for item in self.list_items():
            type_matches = asset_type is None or item.type == asset_type
            symbol_matches = needle in {item.symbol.upper(), item.display.upper()}
            if type_matches and symbol_matches:
                removed.append(item.key())
            else:
                kept.append(item)
        if removed:
            self._save_items(kept)
        return removed

    def _load_payload(self) -> dict:
        if not self.path.exists():
            return {"version": 1, "items": []}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save_items(self, items: list[WatchlistItem]) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "items": [self._item_to_dict(item) for item in items]}
        tmp_path = self.path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp_path, self.path)

    @staticmethod
    def _item_from_dict(record: dict) -> WatchlistItem:
        known = {key: record.get(key) for key in KNOWN_FIELDS if key in record}
        extra = {key: value for key, value in record.items() if key not in KNOWN_FIELDS}
        return WatchlistItem(extra=extra, **known)

    @staticmethod
    def _item_to_dict(item: WatchlistItem) -> dict:
        payload = asdict(item)
        extra = payload.pop("extra")
        payload.update(extra)
        return {key: value for key, value in payload.items() if value is not None}
```

- [ ] **Step 4: Run the watchlist tests**

```bash
cd scripts && uv run --with pytest pytest ../tests/test_watchlist.py -v
```

Expected: pass.

- [ ] **Step 5: Commit if this is a Git repository**

```bash
git status --short
git add scripts/kobserver_core/watchlist.py tests/test_watchlist.py
git commit -m "feat: persist global watchlist"
```

If `git status` reports this is not a Git repository, skip the commit and continue.

## Task 4: CLI Add, Remove, And List

**Files:**
- Modify: `scripts/kobserver_core/cli.py`
- Create: `tests/test_cli_watchlist.py`

- [ ] **Step 1: Write the failing CLI tests**

Create `tests/test_cli_watchlist.py`:

```python
import json

from kobserver_core.cli import main


def test_cli_add_list_remove_json(tmp_path, capsys):
    data_dir = str(tmp_path)

    assert main(["--data-dir", data_dir, "--json", "add", "btc", "--type", "crypto"]) == 0
    added = json.loads(capsys.readouterr().out)
    assert added["added"] is True
    assert added["item"]["symbol"] == "BTC/USD"

    assert main(["--data-dir", data_dir, "--json", "list"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed["count"] == 1
    assert listed["items"][0]["display"] == "BTC"

    assert main(["--data-dir", data_dir, "--json", "remove", "BTC"]) == 0
    removed = json.loads(capsys.readouterr().out)
    assert removed["removed"] == [["crypto", "BTC/USD"]]
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd scripts && uv run --with pytest pytest ../tests/test_cli_watchlist.py -v
```

Expected: fail because `main` only prints help.

- [ ] **Step 3: Implement CLI watchlist commands**

Replace `scripts/kobserver_core/cli.py` with:

```python
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from typing import Any

from kobserver_core.models import WatchlistItem
from kobserver_core.symbols import COMMON_PYTH_FEEDS, normalize_symbol
from kobserver_core.watchlist import WatchlistStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kobserver",
        description="Manage a market watchlist and render quote or candlestick PNGs.",
    )
    parser.add_argument("--data-dir", help="Override the global data directory.")
    parser.add_argument("--timezone", default="Asia/Shanghai")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    add = subparsers.add_parser("add", help="Add a symbol to the watchlist.")
    add.add_argument("symbol")
    add.add_argument("--type", choices=["us", "hk", "crypto"], required=True)
    add.add_argument("--name")

    remove = subparsers.add_parser("remove", help="Remove a symbol from the watchlist.")
    remove.add_argument("symbol")
    remove.add_argument("--type", choices=["us", "hk", "crypto"])

    subparsers.add_parser("list", help="List watchlist items.")

    quotes = subparsers.add_parser("quotes", help="Render the watchlist quote PNG.")
    quotes.add_argument("--output", required=True)
    quotes.add_argument("--width", type=int, default=1600)
    quotes.add_argument("--height", type=int, default=900)

    chart = subparsers.add_parser("chart", help="Render a candlestick PNG for one symbol.")
    chart.add_argument("symbol")
    chart.add_argument("--type", choices=["us", "hk", "crypto"])
    chart.add_argument("--output", required=True)
    chart.add_argument("--interval", default="5m")
    chart.add_argument("--width", type=int, default=1600)
    chart.add_argument("--height", type=int, default=900)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    store = WatchlistStore(args.data_dir, timezone=args.timezone)

    if args.command == "add":
        normalized = normalize_symbol(args.symbol, args.type)
        name = args.name
        if name is None and normalized.type == "crypto":
            name = COMMON_PYTH_FEEDS.get(normalized.symbol, {}).get("name")
        item = WatchlistItem(
            type=normalized.type,
            symbol=normalized.symbol,
            display=normalized.display,
            name=name,
            pyth_id=normalized.pyth_id,
        )
        added = store.add(item)
        return _emit({"added": added, "item": _item_payload(item)}, args.json)

    if args.command == "remove":
        removed = store.remove(args.symbol, args.type)
        return _emit({"removed": [list(key) for key in removed]}, args.json)

    if args.command == "list":
        items = [_item_payload(item) for item in store.list_items()]
        return _emit({"count": len(items), "items": items}, args.json)

    parser.error(f"command not wired yet: {args.command}")
    return 2


def _item_payload(item: WatchlistItem) -> dict[str, Any]:
    payload = asdict(item)
    extra = payload.pop("extra")
    payload.update(extra)
    return {key: value for key, value in payload.items() if value is not None}


def _emit(payload: dict[str, Any], as_json: bool) -> int:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(_plain_text(payload))
    return 0


def _plain_text(payload: dict[str, Any]) -> str:
    if "items" in payload:
        if not payload["items"]:
            return "Watchlist is empty."
        return "\n".join(
            f"{item['type']:7} {item['display']:12} {item.get('name', '')}"
            for item in payload["items"]
        )
    return json.dumps(payload, ensure_ascii=False)
```

- [ ] **Step 4: Run CLI watchlist tests**

```bash
cd scripts && uv run --with pytest pytest ../tests/test_cli_watchlist.py -v
```

Expected: pass.

- [ ] **Step 5: Run all tests built so far**

```bash
cd scripts && uv run --with pytest pytest ../tests/test_cli_smoke.py ../tests/test_symbols.py ../tests/test_watchlist.py ../tests/test_cli_watchlist.py -v
```

Expected: all pass.

- [ ] **Step 6: Commit if this is a Git repository**

```bash
git status --short
git add scripts/kobserver_core/cli.py tests/test_cli_watchlist.py
git commit -m "feat: wire watchlist cli commands"
```

If `git status` reports this is not a Git repository, skip the commit and continue.

## Task 5: Pyth Crypto Provider

**Files:**
- Create: `scripts/kobserver_core/providers.py`
- Create: `tests/test_pyth_provider.py`

- [ ] **Step 1: Write failing Pyth provider tests**

Create `tests/test_pyth_provider.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd scripts && uv run --with pytest pytest ../tests/test_pyth_provider.py -v
```

Expected: fail because `PythProvider` does not exist.

- [ ] **Step 3: Implement PythProvider**

Create `scripts/kobserver_core/providers.py`:

```python
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

from kobserver_core.models import Candle, ChartData, Quote, WatchlistItem

HERMES_BASE_URL = "https://hermes.pyth.network"
PYTH_HISTORY_BASE_URL = "https://pyth.dourolabs.app/v1"


class PythProvider:
    def __init__(self, session=None, timeout: int = 20) -> None:
        self.session = session or requests.Session()
        self.timeout = timeout

    def quote(self, item: WatchlistItem) -> Quote:
        if not item.pyth_id:
            return Quote(
                item=item,
                price=None,
                change=None,
                change_percent=None,
                session="Unavailable",
                source="Pyth",
                error=f"No Pyth feed id for {item.symbol}",
                note="unsupported",
            )
        response = self.session.get(
            f"{HERMES_BASE_URL}/v2/updates/price/latest",
            params={"ids[]": [item.pyth_id]},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        parsed = payload.get("parsed", [])
        if not parsed:
            raise ValueError(f"Pyth returned no parsed price for {item.symbol}")
        price_record = parsed[0]["price"]
        price = float(price_record["price"]) * (10 ** int(price_record["expo"]))
        timestamp = datetime.fromtimestamp(int(price_record["publish_time"]), timezone.utc)
        return Quote(
            item=item,
            price=price,
            change=None,
            change_percent=None,
            session="24/7",
            note="latest",
            timestamp=timestamp,
            source="Pyth",
        )

    def chart(self, item: WatchlistItem, interval: str, timezone_name: str) -> ChartData:
        resolution = _pyth_resolution(interval)
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=24)
        payload = self._history_payload(item.symbol, start, now, resolution)
        candles = _candles_from_history(payload, timezone_name)
        if len(candles) < 2 and resolution == "5":
            payload = self._history_payload(item.symbol, start, now, "15")
            candles = _candles_from_history(payload, timezone_name)
            resolution = "15"
        if len(candles) < 2 and resolution in {"5", "15"}:
            payload = self._history_payload(item.symbol, start, now, "60")
            candles = _candles_from_history(payload, timezone_name)
            resolution = "60"
        return ChartData(
            item=item,
            candles=candles,
            interval=f"{resolution}m" if resolution.isdigit() else resolution,
            range_label="Last 24h",
            source="Pyth",
        )

    def _history_payload(self, symbol: str, start: datetime, end: datetime, resolution: str) -> dict:
        response = self.session.get(
            f"{PYTH_HISTORY_BASE_URL}/real_time/history",
            params={
                "symbol": symbol,
                "from": int(start.timestamp()),
                "to": int(end.timestamp()),
                "resolution": resolution,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()


def _pyth_resolution(interval: str) -> str:
    normalized = interval.strip().lower()
    if normalized.endswith("m"):
        normalized = normalized[:-1]
    if normalized not in {"1", "2", "5", "15", "30", "60", "120", "240", "360", "720", "d", "w", "m"}:
        return "5"
    return normalized.upper() if normalized in {"d", "w", "m"} else normalized


def _candles_from_history(payload: dict, timezone_name: str) -> list[Candle]:
    if payload.get("s") not in {None, "ok"}:
        return []
    times = payload.get("t", [])
    opens = payload.get("o", [])
    highs = payload.get("h", [])
    lows = payload.get("l", [])
    closes = payload.get("c", [])
    volumes = payload.get("v", [])
    tz = ZoneInfo(timezone_name)
    candles: list[Candle] = []
    for index, unix_seconds in enumerate(times):
        volume = volumes[index] if index < len(volumes) else None
        candles.append(
            Candle(
                timestamp=datetime.fromtimestamp(unix_seconds, timezone.utc).astimezone(tz),
                open=float(opens[index]),
                high=float(highs[index]),
                low=float(lows[index]),
                close=float(closes[index]),
                volume=float(volume) if volume is not None else None,
            )
        )
    return candles
```

- [ ] **Step 4: Run Pyth provider tests**

```bash
cd scripts && uv run --with pytest pytest ../tests/test_pyth_provider.py -v
```

Expected: pass.

- [ ] **Step 5: Commit if this is a Git repository**

```bash
git status --short
git add scripts/kobserver_core/providers.py tests/test_pyth_provider.py
git commit -m "feat: add pyth crypto provider"
```

If `git status` reports this is not a Git repository, skip the commit and continue.

## Task 6: Stock Provider

**Files:**
- Modify: `scripts/kobserver_core/providers.py`
- Create: `tests/test_stock_provider.py`

- [ ] **Step 1: Write failing stock provider tests**

Create `tests/test_stock_provider.py`:

```python
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from kobserver_core.models import WatchlistItem
from kobserver_core.providers import StockProvider


class FakeTicker:
    def __init__(self, info, history_frame):
        self.info = info
        self._history_frame = history_frame

    def history(self, *args, **kwargs):
        return self._history_frame


def test_stock_quote_prefers_premarket_when_available():
    frame = pd.DataFrame()
    ticker = FakeTicker(
        {
            "regularMarketPrice": 190.0,
            "regularMarketPreviousClose": 188.0,
            "preMarketPrice": 191.2,
            "shortName": "Apple",
        },
        frame,
    )
    provider = StockProvider(ticker_factory=lambda symbol: ticker)
    item = WatchlistItem(type="us", symbol="AAPL", display="AAPL", name="Apple")

    quote = provider.quote(item)

    assert quote.price == 191.2
    assert round(quote.change, 2) == 3.2
    assert round(quote.change_percent, 4) == 1.7021
    assert quote.session == "Pre"
    assert quote.note == "extended"


def test_stock_chart_converts_history_rows():
    index = pd.DatetimeIndex(
        [datetime(2026, 5, 14, 9, 30), datetime(2026, 5, 14, 9, 35)],
        tz=ZoneInfo("America/New_York"),
    )
    frame = pd.DataFrame(
        {
            "Open": [10.0, 11.0],
            "High": [11.0, 12.0],
            "Low": [9.5, 10.5],
            "Close": [10.8, 11.8],
            "Volume": [1000, 1200],
        },
        index=index,
    )
    ticker = FakeTicker({"shortName": "Test"}, frame)
    provider = StockProvider(ticker_factory=lambda symbol: ticker)
    item = WatchlistItem(type="us", symbol="TEST", display="TEST")

    chart = provider.chart(item, interval="5m", timezone_name="Asia/Shanghai")

    assert chart.source == "Yahoo"
    assert chart.interval == "5m"
    assert len(chart.candles) == 2
    assert chart.candles[0].volume == 1000
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd scripts && uv run --with 'pytest' pytest ../tests/test_stock_provider.py -v
```

Expected: fail because `StockProvider` does not exist.

- [ ] **Step 3: Extend providers.py with StockProvider**

Append this to `scripts/kobserver_core/providers.py`:

```python
class StockProvider:
    def __init__(self, ticker_factory=None) -> None:
        if ticker_factory is None:
            import yfinance as yf

            ticker_factory = yf.Ticker
        self.ticker_factory = ticker_factory

    def quote(self, item: WatchlistItem) -> Quote:
        ticker = self.ticker_factory(item.symbol)
        info = getattr(ticker, "info", {}) or {}
        previous_close = _float_or_none(info.get("regularMarketPreviousClose") or info.get("previousClose"))
        regular = _float_or_none(info.get("regularMarketPrice") or info.get("currentPrice"))
        pre = _float_or_none(info.get("preMarketPrice"))
        after = _float_or_none(info.get("postMarketPrice"))

        session = "Closed"
        note = "last close"
        price = regular if regular is not None else previous_close
        if pre is not None:
            price = pre
            session = "Pre"
            note = "extended"
        elif after is not None:
            price = after
            session = "After"
            note = "extended"
        elif regular is not None:
            session = "Regular"
            note = ""

        change = None
        change_percent = None
        if price is not None and previous_close not in {None, 0}:
            change = price - previous_close
            change_percent = change / previous_close * 100

        return Quote(
            item=item,
            price=price,
            change=change,
            change_percent=change_percent,
            session=session,
            note=note,
            source="Yahoo",
        )

    def chart(self, item: WatchlistItem, interval: str, timezone_name: str) -> ChartData:
        ticker = self.ticker_factory(item.symbol)
        frame = ticker.history(period="1d", interval=interval, prepost=True)
        if frame.empty:
            frame = ticker.history(period="5d", interval=interval, prepost=True)
        candles = _candles_from_yfinance(frame, timezone_name)
        return ChartData(
            item=item,
            candles=candles,
            interval=interval,
            range_label="Current or previous trading day",
            source="Yahoo",
        )


def _float_or_none(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _candles_from_yfinance(frame, timezone_name: str) -> list[Candle]:
    if frame is None or frame.empty:
        return []
    tz = ZoneInfo(timezone_name)
    candles: list[Candle] = []
    for timestamp, row in frame.iterrows():
        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize(timezone.utc)
        else:
            timestamp = timestamp.tz_convert(timezone.utc)
        volume_value = row.get("Volume")
        candles.append(
            Candle(
                timestamp=timestamp.to_pydatetime().astimezone(tz),
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=float(volume_value) if volume_value is not None else None,
            )
        )
    return candles
```

- [ ] **Step 4: Run stock provider tests**

```bash
cd scripts && uv run --with pytest pytest ../tests/test_stock_provider.py -v
```

Expected: pass.

- [ ] **Step 5: Run Pyth provider tests again**

```bash
cd scripts && uv run --with pytest pytest ../tests/test_pyth_provider.py -v
```

Expected: pass.

- [ ] **Step 6: Commit if this is a Git repository**

```bash
git status --short
git add scripts/kobserver_core/providers.py tests/test_stock_provider.py
git commit -m "feat: add stock provider"
```

If `git status` reports this is not a Git repository, skip the commit and continue.

## Task 7: PNG Rendering

**Files:**
- Create: `scripts/kobserver_core/rendering.py`
- Create: `tests/test_rendering.py`

- [ ] **Step 1: Write failing renderer tests**

Create `tests/test_rendering.py`:

```python
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image

from kobserver_core.models import Candle, ChartData, Quote, WatchlistItem
from kobserver_core.rendering import render_chart_png, render_error_png, render_quotes_png


def assert_valid_png(path: Path):
    assert path.exists()
    assert path.stat().st_size > 1000
    with Image.open(path) as image:
        assert image.format == "PNG"
        assert image.width > 100
        assert image.height > 100


def test_render_quotes_png_without_source_column(tmp_path):
    item = WatchlistItem(type="crypto", symbol="BTC/USD", display="BTC", name="Bitcoin")
    quote = Quote(
        item=item,
        price=64120.0,
        change=120.0,
        change_percent=0.19,
        session="24/7",
        note="24h",
        source="Pyth",
    )
    output = tmp_path / "quotes.png"

    render_quotes_png([quote], output, timezone_name="Asia/Shanghai", width=1200, height=700)

    assert_valid_png(output)


def test_render_chart_png_with_axes(tmp_path):
    item = WatchlistItem(type="crypto", symbol="BTC/USD", display="BTC", name="Bitcoin")
    tz = ZoneInfo("Asia/Shanghai")
    chart = ChartData(
        item=item,
        interval="5m",
        range_label="Last 24h",
        source="Pyth",
        candles=[
            Candle(datetime(2026, 5, 14, 8, 0, tzinfo=tz), 10, 12, 9, 11),
            Candle(datetime(2026, 5, 14, 8, 5, tzinfo=tz), 11, 13, 10, 12),
            Candle(datetime(2026, 5, 14, 8, 10, tzinfo=tz), 12, 14, 11, 13),
        ],
    )
    output = tmp_path / "chart.png"

    render_chart_png(chart, output, width=1200, height=700)

    assert_valid_png(output)


def test_render_error_png(tmp_path):
    output = tmp_path / "error.png"

    render_error_png("BTC", "No usable chart data", output, width=900, height=500)

    assert_valid_png(output)
```

- [ ] **Step 2: Run renderer tests to verify they fail**

```bash
cd scripts && uv run --with pytest pytest ../tests/test_rendering.py -v
```

Expected: fail because `rendering.py` does not exist.

- [ ] **Step 3: Implement rendering**

Create `scripts/kobserver_core/rendering.py`:

```python
from __future__ import annotations

from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from kobserver_core.models import ChartData, Quote

GREEN = "#1a7f37"
RED = "#cf222e"
TEXT = "#24292f"
MUTED = "#6e7781"
GRID = "#d0d7de"


def render_quotes_png(
    quotes: list[Quote],
    output: str | Path,
    timezone_name: str,
    width: int,
    height: int,
) -> None:
    output = Path(output)
    dpi = 160
    fig_width = width / dpi
    fig_height = height / dpi
    fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=dpi)
    ax.axis("off")
    ax.text(0.02, 0.96, "Kobserver Watchlist", fontsize=20, weight="bold", color=TEXT, transform=ax.transAxes)
    now_label = _now_label(timezone_name)
    ax.text(0.02, 0.91, now_label, fontsize=10, color=MUTED, transform=ax.transAxes)

    columns = ["Symbol", "Name", "Price", "Change", "Session", "Note"]
    rows = []
    for quote in quotes:
        rows.append(
            [
                quote.item.display,
                quote.item.name or "",
                _price_text(quote.price),
                _change_text(quote.change, quote.change_percent),
                quote.session,
                quote.note or quote.error or "",
            ]
        )
    table = ax.table(
        cellText=rows,
        colLabels=columns,
        loc="center",
        cellLoc="left",
        colLoc="left",
        colWidths=[0.14, 0.22, 0.15, 0.15, 0.14, 0.20],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.5)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor(GRID)
        if row == 0:
            cell.set_facecolor("#f6f8fa")
            cell.set_text_props(weight="bold", color=TEXT)
        elif col == 3:
            text = cell.get_text().get_text()
            if text.startswith("+"):
                cell.set_text_props(color=GREEN)
            elif text.startswith("-"):
                cell.set_text_props(color=RED)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def render_chart_png(chart: ChartData, output: str | Path, width: int, height: int) -> None:
    if not chart.candles:
        render_error_png(chart.item.display, "No usable chart data", output, width, height)
        return
    output = Path(output)
    dpi = 160
    fig_width = width / dpi
    fig_height = height / dpi
    has_volume = any(candle.volume is not None for candle in chart.candles)
    if has_volume:
        fig, (ax, volume_ax) = plt.subplots(
            2,
            1,
            figsize=(fig_width, fig_height),
            dpi=dpi,
            sharex=True,
            gridspec_kw={"height_ratios": [4, 1]},
        )
    else:
        fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=dpi)
        volume_ax = None

    fig.suptitle(f"{chart.item.display} - {chart.range_label}", fontsize=18, weight="bold", color=TEXT)
    ax.set_title(f"{chart.interval} candles", fontsize=10, color=MUTED)
    xs = [mdates.date2num(candle.timestamp) for candle in chart.candles]
    candle_width = _candle_width(xs)
    for x, candle in zip(xs, chart.candles):
        color = GREEN if candle.close >= candle.open else RED
        ax.vlines(x, candle.low, candle.high, color=color, linewidth=1)
        body_low = min(candle.open, candle.close)
        body_height = max(abs(candle.close - candle.open), 0.000001)
        ax.add_patch(
            Rectangle(
                (x - candle_width / 2, body_low),
                candle_width,
                body_height,
                facecolor=color,
                edgecolor=color,
                linewidth=0.8,
            )
        )
    ax.yaxis.tick_right()
    ax.yaxis.set_label_position("right")
    ax.grid(True, color=GRID, alpha=0.6)
    ax.set_ylabel("Price")

    if volume_ax is not None:
        volumes = [candle.volume or 0 for candle in chart.candles]
        volume_ax.bar(xs, volumes, width=candle_width, color="#8c959f", alpha=0.55)
        volume_ax.grid(True, color=GRID, alpha=0.4)
        volume_ax.set_ylabel("Vol")

    target_ax = volume_ax or ax
    target_ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    target_ax.set_xlabel("Time")
    fig.autofmt_xdate()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def render_error_png(symbol: str, message: str, output: str | Path, width: int, height: int) -> None:
    output = Path(output)
    dpi = 160
    fig, ax = plt.subplots(figsize=(width / dpi, height / dpi), dpi=dpi)
    ax.axis("off")
    ax.text(0.5, 0.58, f"{symbol}", ha="center", va="center", fontsize=24, weight="bold", color=TEXT)
    ax.text(0.5, 0.43, message, ha="center", va="center", fontsize=13, color=MUTED, wrap=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _now_label(timezone_name: str) -> str:
    from datetime import datetime

    return f"{datetime.now(ZoneInfo(timezone_name)).strftime('%Y-%m-%d %H:%M')} {timezone_name}"


def _price_text(price: float | None) -> str:
    if price is None:
        return "Unavailable"
    return f"{price:,.2f}"


def _change_text(change: float | None, change_percent: float | None) -> str:
    if change is None or change_percent is None:
        return ""
    return f"{change:+.2f} ({change_percent:+.2f}%)"


def _candle_width(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.002
    return max((xs[1] - xs[0]) * 0.65, 0.0005)
```

- [ ] **Step 4: Run renderer tests**

```bash
cd scripts && uv run --with pytest pytest ../tests/test_rendering.py -v
```

Expected: pass.

- [ ] **Step 5: Commit if this is a Git repository**

```bash
git status --short
git add scripts/kobserver_core/rendering.py tests/test_rendering.py
git commit -m "feat: render quote and chart images"
```

If `git status` reports this is not a Git repository, skip the commit and continue.

## Task 8: Wire Quotes And Chart CLI

**Files:**
- Modify: `scripts/kobserver_core/cli.py`
- Modify: `scripts/kobserver_core/providers.py`
- Create: `tests/test_cli_render_commands.py`

- [ ] **Step 1: Write failing command orchestration tests**

Create `tests/test_cli_render_commands.py`:

```python
import json

from PIL import Image

from kobserver_core import cli
from kobserver_core.models import ChartData, Quote, WatchlistItem


class FakeStockProvider:
    def quote(self, item):
        return Quote(item=item, price=10.0, change=1.0, change_percent=10.0, session="Regular", source="Yahoo")

    def chart(self, item, interval, timezone_name):
        return ChartData(item=item, candles=[], interval=interval, range_label="Current or previous trading day", source="Yahoo")


class FakePythProvider:
    def quote(self, item):
        return Quote(item=item, price=64120.0, change=None, change_percent=None, session="24/7", note="latest", source="Pyth")

    def chart(self, item, interval, timezone_name):
        return ChartData(item=item, candles=[], interval=interval, range_label="Last 24h", source="Pyth")


def test_cli_quotes_renders_png(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "StockProvider", lambda: FakeStockProvider())
    monkeypatch.setattr(cli, "PythProvider", lambda: FakePythProvider())
    data_dir = str(tmp_path / "data")
    output = tmp_path / "quotes.png"
    cli.main(["--data-dir", data_dir, "add", "AAPL", "--type", "us"])
    cli.main(["--data-dir", data_dir, "add", "BTC", "--type", "crypto"])

    assert cli.main(["--data-dir", data_dir, "--json", "quotes", "--output", str(output)]) == 0
    payload = json.loads(capsys.readouterr().out.splitlines()[-1])

    assert payload["output"] == str(output)
    assert payload["ok"] == 2
    with Image.open(output) as image:
        assert image.format == "PNG"


def test_cli_chart_renders_error_png_for_empty_chart(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "PythProvider", lambda: FakePythProvider())
    data_dir = str(tmp_path / "data")
    output = tmp_path / "chart.png"
    cli.main(["--data-dir", data_dir, "add", "BTC", "--type", "crypto"])

    assert cli.main(["--data-dir", data_dir, "--json", "chart", "BTC", "--output", str(output)]) == 0
    payload = json.loads(capsys.readouterr().out.splitlines()[-1])

    assert payload["output"] == str(output)
    assert payload["symbol"] == "BTC"
    with Image.open(output) as image:
        assert image.format == "PNG"
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd scripts && uv run --with pytest pytest ../tests/test_cli_render_commands.py -v
```

Expected: fail because `quotes` and `chart` are not wired.

- [ ] **Step 3: Update provider error isolation**

Add this helper to `scripts/kobserver_core/providers.py`:

```python
def quote_error(item: WatchlistItem, source: str, error: Exception) -> Quote:
    return Quote(
        item=item,
        price=None,
        change=None,
        change_percent=None,
        session="Unavailable",
        note=error.__class__.__name__,
        source=source,
        error=str(error),
    )
```

- [ ] **Step 4: Wire quotes and chart in the CLI**

Modify `scripts/kobserver_core/cli.py` imports:

```python
from pathlib import Path

from kobserver_core.providers import PythProvider, StockProvider, quote_error
from kobserver_core.rendering import render_chart_png, render_error_png, render_quotes_png
```

Add this branch inside `main` before `parser.error(...)`:

```python
    if args.command == "quotes":
        items = store.list_items()
        stock_provider = StockProvider()
        pyth_provider = PythProvider()
        quotes = []
        for item in items:
            provider = pyth_provider if item.type == "crypto" else stock_provider
            source = "Pyth" if item.type == "crypto" else "Yahoo"
            try:
                quotes.append(provider.quote(item))
            except Exception as exc:
                quotes.append(quote_error(item, source, exc))
        render_quotes_png(quotes, Path(args.output), args.timezone, args.width, args.height)
        payload = {
            "output": str(args.output),
            "ok": sum(1 for quote in quotes if quote.error is None),
            "failed": sum(1 for quote in quotes if quote.error is not None),
            "items": [
                {
                    "symbol": quote.item.display,
                    "price": quote.price,
                    "session": quote.session,
                    "note": quote.note,
                    "source": quote.source,
                    "error": quote.error,
                }
                for quote in quotes
            ],
        }
        return _emit(payload, args.json)

    if args.command == "chart":
        item = _find_chart_item(store.list_items(), args.symbol, args.type)
        if item is None:
            normalized_type = args.type or ("crypto" if "/" in args.symbol or args.symbol.upper() in COMMON_PYTH_FEEDS else "us")
            normalized = normalize_symbol(args.symbol, normalized_type)
            item = WatchlistItem(
                type=normalized.type,
                symbol=normalized.symbol,
                display=normalized.display,
                pyth_id=normalized.pyth_id,
            )
        provider = PythProvider() if item.type == "crypto" else StockProvider()
        try:
            chart_data = provider.chart(item, args.interval, args.timezone)
            if chart_data.candles:
                render_chart_png(chart_data, Path(args.output), args.width, args.height)
                status = "ok"
                error = None
            else:
                render_error_png(item.display, "No usable chart data", Path(args.output), args.width, args.height)
                status = "error"
                error = "No usable chart data"
        except Exception as exc:
            render_error_png(item.display, str(exc), Path(args.output), args.width, args.height)
            status = "error"
            error = str(exc)
        return _emit(
            {
                "output": str(args.output),
                "symbol": item.display,
                "status": status,
                "error": error,
            },
            args.json,
        )
```

Add this helper near the bottom of `scripts/kobserver_core/cli.py`:

```python
def _find_chart_item(items: list[WatchlistItem], symbol: str, asset_type: str | None) -> WatchlistItem | None:
    needle = symbol.strip().upper()
    for item in items:
        if asset_type is not None and item.type != asset_type:
            continue
        if needle in {item.symbol.upper(), item.display.upper()}:
            return item
    return None
```

- [ ] **Step 5: Run render command tests**

```bash
cd scripts && uv run --with pytest pytest ../tests/test_cli_render_commands.py -v
```

Expected: pass.

- [ ] **Step 6: Run all Python tests**

```bash
cd scripts && uv run --with pytest pytest ../tests -v
```

Expected: all pass.

- [ ] **Step 7: Commit if this is a Git repository**

```bash
git status --short
git add scripts/kobserver_core/cli.py scripts/kobserver_core/providers.py tests/test_cli_render_commands.py
git commit -m "feat: wire render commands"
```

If `git status` reports this is not a Git repository, skip the commit and continue.

## Task 9: OpenClaw Skill Metadata And References

**Files:**
- Create: `SKILL.md`
- Create: `agents/openai.yaml`
- Create: `references/data-sources.md`
- Create: `tests/test_skill_metadata.py`

- [ ] **Step 1: Write failing metadata tests**

Create `tests/test_skill_metadata.py`:

```python
from pathlib import Path


def test_skill_md_declares_kobserver_and_uv():
    text = Path("../SKILL.md").read_text(encoding="utf-8")
    assert "name: kobserver" in text
    assert '"bins": ["uv"]' in text
    assert "{baseDir}/scripts" in text
    assert "quotes" in text
    assert "chart" in text


def test_openai_yaml_exists():
    text = Path("../agents/openai.yaml").read_text(encoding="utf-8")
    assert "display_name: Kobserver" in text
    assert "default_prompt:" in text
```

- [ ] **Step 2: Run metadata tests to verify they fail**

```bash
cd scripts && uv run --with pytest pytest ../tests/test_skill_metadata.py -v
```

Expected: fail because skill metadata files do not exist.

- [ ] **Step 3: Create SKILL.md**

Create `SKILL.md`:

```markdown
---
name: kobserver
description: Manage a global market watchlist for US stocks, Hong Kong stocks, and crypto; render watchlist quotes or single-symbol candlestick charts as PNG images using a bundled Python CLI.
metadata: { "openclaw": { "emoji": "📈", "requires": { "bins": ["uv"] }, "install": [ { "id": "uv", "kind": "brew", "formula": "uv", "bins": ["uv"], "label": "Install uv (brew)" } ] } }
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
```

- [ ] **Step 4: Create UI metadata and data-source reference**

Create `agents/openai.yaml`:

```yaml
display_name: Kobserver
short_description: Manage a market watchlist and render quotes or candlestick charts.
default_prompt: Show my Kobserver watchlist as an image.
```

Create `references/data-sources.md`:

```markdown
# Kobserver Data Sources

Stocks use `yfinance`, which depends on Yahoo-compatible public data. Pre-market, after-hours, and overnight fields are best-effort; when the provider omits them, use regular or latest close data and mark the quote note.

Crypto uses Pyth public APIs rather than CEX APIs. Latest prices come from Hermes `/v2/updates/price/latest` by feed ID. Candlesticks come from Pyth History `/v1/real_time/history` with TradingView-style OHLC arrays.

The first version bundles common Pyth feed IDs for BTC/USD, ETH/USD, and SOL/USD. For unsupported crypto symbols, the CLI should return a clear unsupported-symbol message.
```

- [ ] **Step 5: Run metadata tests**

```bash
cd scripts && uv run --with pytest pytest ../tests/test_skill_metadata.py -v
```

Expected: pass.

- [ ] **Step 6: Commit if this is a Git repository**

```bash
git status --short
git add SKILL.md agents/openai.yaml references/data-sources.md tests/test_skill_metadata.py
git commit -m "docs: add openclaw skill metadata"
```

If `git status` reports this is not a Git repository, skip the commit and continue.

## Task 10: Final Verification And Smoke Commands

**Files:**
- Modify if needed: files touched by earlier tasks

- [ ] **Step 1: Run the full automated test suite**

```bash
cd scripts && uv run --with pytest pytest ../tests -v
```

Expected: all tests pass.

- [ ] **Step 2: Run local CLI smoke commands with isolated data**

```bash
cd scripts
tmp_dir="$(mktemp -d)"
uv run python kobserver.py --data-dir "$tmp_dir" --json add AAPL --type us
uv run python kobserver.py --data-dir "$tmp_dir" --json add 0700 --type hk
uv run python kobserver.py --data-dir "$tmp_dir" --json add BTC --type crypto
uv run python kobserver.py --data-dir "$tmp_dir" --json list
```

Expected: JSON output lists `AAPL`, `0700.HK`, and `BTC/USD`.

- [ ] **Step 3: Render offline-safe test images through tests**

```bash
cd scripts && uv run --with pytest pytest ../tests/test_rendering.py -v
```

Expected: generated temporary PNGs are valid.

- [ ] **Step 4: Optional live data smoke test**

Run only if network is available:

```bash
cd scripts
tmp_dir="$(mktemp -d)"
uv run python kobserver.py --data-dir "$tmp_dir" --json add BTC --type crypto
uv run python kobserver.py --data-dir "$tmp_dir" --json quotes --output /tmp/kobserver-quotes.png
uv run python kobserver.py --data-dir "$tmp_dir" --json chart BTC --output /tmp/kobserver-btc.png
```

Expected: `/tmp/kobserver-quotes.png` and `/tmp/kobserver-btc.png` exist and are non-empty. The chart has a bottom time axis and a right-side price axis.

- [ ] **Step 5: Inspect final file list**

```bash
find . -maxdepth 4 -type f | sort
```

Expected: project contains `SKILL.md`, `agents/openai.yaml`, `references/data-sources.md`, `scripts/kobserver.py`, `scripts/pyproject.toml`, `scripts/kobserver_core/*.py`, and `tests/*.py`.

- [ ] **Step 6: Commit if this is a Git repository**

```bash
git status --short
git add SKILL.md agents/openai.yaml references/data-sources.md scripts tests docs/superpowers
git commit -m "feat: build kobserver openclaw skill"
```

If `git status` reports this is not a Git repository, skip the commit and report the working tree contents.

## Self-Review Notes

Spec coverage:

- Global watchlist storage maps to Tasks 3 and 4.
- US/HK yfinance provider maps to Task 6.
- Pyth crypto latest and candles map to Task 5.
- Quote PNG without `Source` column maps to Task 7.
- Candlestick axes map to Task 7.
- OpenClaw installable skill metadata maps to Task 9.
- Tests and smoke verification map to Tasks 1 through 10.

Execution notes:

- This workspace was not a Git repository during planning. Commit steps are included for future repository use and should be skipped when Git is unavailable.
- Live API tests are optional smoke checks. Automated tests use mocks and local rendering.
