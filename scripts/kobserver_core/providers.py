from __future__ import annotations

import os
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

from kobserver_core.models import Candle, ChartData, Quote, WatchlistItem

FINNHUB_BASE_URL = "https://finnhub.io/api/v1"
HERMES_BASE_URL = "https://hermes.pyth.network"
PYTH_HISTORY_BASE_URL = "https://pyth.dourolabs.app/v1"


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
        history_symbol = _pyth_history_symbol(item.symbol)
        payload = self._history_payload(history_symbol, start, now, resolution)
        candles = _candles_from_history(payload, timezone_name)
        if len(candles) < 2 and resolution == "5":
            payload = self._history_payload(history_symbol, start, now, "15")
            candles = _candles_from_history(payload, timezone_name)
            resolution = "15"
        if len(candles) < 2 and resolution in {"5", "15"}:
            payload = self._history_payload(history_symbol, start, now, "60")
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


def _pyth_history_symbol(symbol: str) -> str:
    if "." in symbol.split("/", 1)[0]:
        return symbol
    return f"Crypto.{symbol}"


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


class StockProvider:
    def __init__(self, token: str | None = None, session=None, timeout: int = 20, now_fn=None) -> None:
        self.token = token or os.environ.get("FINNHUB_API_KEY") or os.environ.get("FINNHUB_TOKEN")
        self.session = session or requests.Session()
        self.timeout = timeout
        self.now_fn = now_fn or (lambda: datetime.now(timezone.utc))

    def quote(self, item: WatchlistItem) -> Quote:
        payload = self._get("/quote", {"symbol": item.symbol})
        price = _float_or_none(payload.get("c"))
        previous_close = _float_or_none(payload.get("pc"))
        change = _float_or_none(payload.get("d"))
        change_percent = _float_or_none(payload.get("dp"))
        timestamp = _timestamp_or_none(payload.get("t"))
        if _empty_finnhub_quote(price, previous_close, timestamp):
            raise ValueError(f"No usable Finnhub quote for {item.symbol}")
        session, note = _stock_session(item, timestamp, price)

        if price is None and previous_close is not None:
            price = previous_close
            session = "Closed"
            note = "last close"
        if change is None and price is not None and previous_close not in {None, 0}:
            change = price - previous_close
        if change_percent is None and change is not None and previous_close not in {None, 0}:
            change_percent = change / previous_close * 100

        return Quote(
            item=item,
            price=price,
            change=change,
            change_percent=change_percent,
            session=session,
            note=note,
            timestamp=timestamp,
            source="Finnhub",
        )

    def chart(self, item: WatchlistItem, interval: str, timezone_name: str) -> ChartData:
        now = self.now_fn()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        now = now.astimezone(timezone.utc)
        start = now - timedelta(days=5)
        resolution = _finnhub_resolution(interval)
        payload = self._get(
            "/stock/candle",
            {
                "symbol": item.symbol,
                "resolution": resolution,
                "from": int(start.timestamp()),
                "to": int(now.timestamp()),
            },
        )
        candles = _latest_trading_day(_candles_from_finnhub(payload, timezone_name))
        return ChartData(
            item=item,
            candles=candles,
            interval=interval,
            range_label="Current or previous trading day",
            source="Finnhub",
        )

    def _get(self, path: str, params: dict) -> dict:
        token = self._require_token()
        response = self.session.get(
            f"{FINNHUB_BASE_URL}{path}",
            params={**params, "token": token},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def _require_token(self) -> str:
        if not self.token:
            raise ValueError("Missing FINNHUB_API_KEY. Set FINNHUB_API_KEY or FINNHUB_TOKEN before requesting stock data.")
        return self.token


def _float_or_none(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _timestamp_or_none(value) -> datetime | None:
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return None
    if timestamp <= 0:
        return None
    return datetime.fromtimestamp(timestamp, timezone.utc)


def _empty_finnhub_quote(price: float | None, previous_close: float | None, timestamp: datetime | None) -> bool:
    return price in {None, 0} and previous_close in {None, 0} and timestamp is None


def _finnhub_resolution(interval: str) -> str:
    normalized = interval.strip().lower()
    if normalized.endswith("m"):
        normalized = normalized[:-1]
    if normalized in {"1", "5", "15", "30", "60", "d", "w", "m"}:
        return normalized.upper() if normalized in {"d", "w", "m"} else normalized
    return "5"


def _stock_session(item: WatchlistItem, timestamp: datetime | None, price: float | None) -> tuple[str, str]:
    if price is None:
        return "Unavailable", ""
    if timestamp is None:
        return "Regular", ""
    if item.type == "us":
        local_time = timestamp.astimezone(ZoneInfo("America/New_York"))
        if local_time.weekday() >= 5:
            return "Closed", "latest"
        clock = local_time.time()
        if time(4, 0) <= clock < time(9, 30):
            return "Pre", "extended"
        if time(9, 30) <= clock <= time(16, 0):
            return "Regular", ""
        if time(16, 0) < clock <= time(20, 0):
            return "After", "extended"
        return "Closed", "latest"
    if item.type == "hk":
        local_time = timestamp.astimezone(ZoneInfo("Asia/Hong_Kong"))
        if local_time.weekday() >= 5:
            return "Closed", "latest"
        clock = local_time.time()
        if time(9, 30) <= clock < time(12, 0) or time(13, 0) <= clock <= time(16, 0):
            return "Regular", ""
        return "Closed", "latest"
    return "Regular", ""


def _candles_from_finnhub(payload: dict, timezone_name: str) -> list[Candle]:
    if payload.get("s") != "ok":
        return []
    tz = ZoneInfo(timezone_name)
    times = payload.get("t", [])
    opens = payload.get("o", [])
    highs = payload.get("h", [])
    lows = payload.get("l", [])
    closes = payload.get("c", [])
    volumes = payload.get("v", [])
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


def _latest_trading_day(candles: list[Candle]) -> list[Candle]:
    if not candles:
        return []
    latest_date = candles[-1].timestamp.date()
    return [candle for candle in candles if candle.timestamp.date() == latest_date]
