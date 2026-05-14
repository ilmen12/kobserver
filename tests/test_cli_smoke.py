from kobserver_core.cli import build_parser


def test_parser_has_expected_subcommands():
    parser = build_parser()
    subparsers = [
        action
        for action in parser._actions
        if action.__class__.__name__ == "_SubParsersAction"
    ]
    assert len(subparsers) == 1
    assert {"add", "remove", "list", "quotes", "chart"} <= set(subparsers[0].choices)
