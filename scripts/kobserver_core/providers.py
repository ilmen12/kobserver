from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

from kobserver_core.models import Candle, ChartData, Quote, WatchlistItem

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
            frame = _latest_session_frame(frame)
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


def _latest_session_frame(frame):
    if frame is None or frame.empty:
        return frame
    latest_date = frame.index[-1].date()
    mask = [timestamp.date() == latest_date for timestamp in frame.index]
    return frame.loc[mask]
