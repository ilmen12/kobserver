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


def test_cli_add_and_remove_accept_prefixed_tokens(tmp_path, capsys):
    data_dir = str(tmp_path)

    assert main(["--data-dir", data_dir, "--json", "add", "us:aapl"]) == 0
    added = json.loads(capsys.readouterr().out)
    assert added["item"]["type"] == "us"
    assert added["item"]["symbol"] == "AAPL"

    assert main(["--data-dir", data_dir, "--json", "remove", "us:AAPL"]) == 0
    removed = json.loads(capsys.readouterr().out)
    assert removed["removed"] == [["us", "AAPL"]]


def test_cli_replace_accepts_mixed_prefixed_tokens_and_preserves_order(tmp_path, capsys):
    data_dir = str(tmp_path)
    main(["--data-dir", data_dir, "--json", "add", "OLD", "--type", "us"])
    capsys.readouterr()

    assert (
        main(
            [
                "--data-dir",
                data_dir,
                "--json",
                "replace",
                "us:AAPL",
                "crypto:BTC",
                "hk:700",
                "us:MSFT",
            ]
        )
        == 0
    )
    replaced = json.loads(capsys.readouterr().out)

    assert replaced["replaced"] is True
    assert replaced["count"] == 4
    assert [(item["type"], item["symbol"]) for item in replaced["items"]] == [
        ("us", "AAPL"),
        ("crypto", "BTC/USD"),
        ("hk", "0700.HK"),
        ("us", "MSFT"),
    ]


def test_cli_replace_deduplicates_mixed_prefixed_tokens(tmp_path, capsys):
    data_dir = str(tmp_path)

    assert main(["--data-dir", data_dir, "--json", "replace", "us:AAPL", "us:aapl", "crypto:BTC"]) == 0
    replaced = json.loads(capsys.readouterr().out)

    assert replaced["count"] == 2
    assert [(item["type"], item["symbol"]) for item in replaced["items"]] == [
        ("us", "AAPL"),
        ("crypto", "BTC/USD"),
    ]
