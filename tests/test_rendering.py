from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image

from kobserver_core.models import Candle, ChartData, Quote, WatchlistItem
from kobserver_core.rendering import _has_volume, render_chart_png, render_error_png, render_quotes_png


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


def test_zero_volume_is_treated_as_no_volume():
    tz = ZoneInfo("Asia/Shanghai")
    candles = [
        Candle(datetime(2026, 5, 14, 8, 0, tzinfo=tz), 10, 12, 9, 11, volume=0),
        Candle(datetime(2026, 5, 14, 8, 5, tzinfo=tz), 11, 13, 10, 12, volume=0),
    ]

    assert _has_volume(candles) is False
