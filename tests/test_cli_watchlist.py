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
