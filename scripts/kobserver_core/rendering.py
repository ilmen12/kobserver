from __future__ import annotations

from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from kobserver_core.models import Candle, ChartData, Quote

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
    ax.text(0.02, 0.91, _now_label(timezone_name), fontsize=10, color=MUTED, transform=ax.transAxes)

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
    has_volume = _has_volume(chart.candles)
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


def _has_volume(candles: list[Candle]) -> bool:
    return any((candle.volume or 0) > 0 for candle in candles)
