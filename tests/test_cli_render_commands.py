import json

from PIL import Image

from kobserver_core import cli
from kobserver_core.models import ChartData, Quote


class FakeStockProvider:
    def quote(self, item):
        return Quote(item=item, price=10.0, change=1.0, change_percent=10.0, session="Regular", source="Yahoo")

    def chart(self, item, interval, timezone_name):
        return ChartData(
            item=item,
            candles=[],
            interval=interval,
            range_label="Current or previous trading day",
            source="Yahoo",
        )


class FakePythProvider:
    def quote(self, item):
        return Quote(
            item=item,
            price=64120.0,
            change=None,
            change_percent=None,
            session="24/7",
            note="latest",
            source="Pyth",
        )

    def chart(self, item, interval, timezone_name):
        return ChartData(item=item, candles=[], interval=interval, range_label="Last 24h", source="Pyth")


def test_cli_quotes_renders_png(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "StockProvider", lambda: FakeStockProvider())
    monkeypatch.setattr(cli, "PythProvider", lambda: FakePythProvider())
    data_dir = str(tmp_path / "data")
    output = tmp_path / "quotes.png"
    cli.main(["--data-dir", data_dir, "add", "AAPL", "--type", "us"])
    cli.main(["--data-dir", data_dir, "add", "BTC", "--type", "crypto"])
    capsys.readouterr()

    assert cli.main(["--data-dir", data_dir, "--json", "quotes", "--output", str(output)]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["output"] == str(output)
    assert payload["ok"] == 2
    with Image.open(output) as image:
        assert image.format == "PNG"


def test_cli_chart_renders_error_png_for_empty_chart(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "PythProvider", lambda: FakePythProvider())
    data_dir = str(tmp_path / "data")
    output = tmp_path / "chart.png"
    cli.main(["--data-dir", data_dir, "add", "BTC", "--type", "crypto"])
    capsys.readouterr()

    assert cli.main(["--data-dir", data_dir, "--json", "chart", "BTC", "--output", str(output)]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["output"] == str(output)
    assert payload["symbol"] == "BTC"
    with Image.open(output) as image:
        assert image.format == "PNG"


def test_cli_chart_accepts_prefixed_symbol_token(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "PythProvider", lambda: FakePythProvider())
    data_dir = str(tmp_path / "data")
    output = tmp_path / "chart.png"
    cli.main(["--data-dir", data_dir, "replace", "crypto:BTC"])
    capsys.readouterr()

    assert cli.main(["--data-dir", data_dir, "--json", "chart", "crypto:BTC", "--output", str(output)]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["symbol"] == "BTC"
    with Image.open(output) as image:
        assert image.format == "PNG"


def test_cli_chart_prefixed_token_works_without_watchlist_item(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "PythProvider", lambda: FakePythProvider())
    data_dir = str(tmp_path / "data")
    output = tmp_path / "chart.png"

    assert cli.main(["--data-dir", data_dir, "--json", "chart", "crypto:BTC", "--output", str(output)]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["symbol"] == "BTC"
    with Image.open(output) as image:
        assert image.format == "PNG"
