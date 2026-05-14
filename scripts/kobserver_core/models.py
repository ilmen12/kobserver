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
