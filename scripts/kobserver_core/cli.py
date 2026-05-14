from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from kobserver_core.models import WatchlistItem
from kobserver_core.providers import PythProvider, StockProvider, quote_error
from kobserver_core.rendering import render_chart_png, render_error_png, render_quotes_png
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
            normalized_type = _infer_asset_type(args.symbol, args.type)
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


def _find_chart_item(items: list[WatchlistItem], symbol: str, asset_type: str | None) -> WatchlistItem | None:
    needle = symbol.strip().upper()
    for item in items:
        if asset_type is not None and item.type != asset_type:
            continue
        if needle in {item.symbol.upper(), item.display.upper()}:
            return item
    return None


def _infer_asset_type(symbol: str, explicit_type: str | None) -> str:
    if explicit_type is not None:
        return explicit_type
    normalized = symbol.strip().upper()
    if normalized in COMMON_PYTH_FEEDS or f"{normalized}/USD" in COMMON_PYTH_FEEDS or "/" in normalized:
        return "crypto"
    if normalized.endswith(".HK") or normalized.isdigit():
        return "hk"
    return "us"
