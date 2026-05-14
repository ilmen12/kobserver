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
