from unittest.mock import MagicMock, patch

from app.main import build_parser, main


def test_cli_parser_accepts_run_once_topic():
    args = build_parser().parse_args(["--run-once", "--topic", "AI tools"])

    assert args.run_once is True
    assert args.topic == "AI tools"


def test_cli_rejects_topic_without_run_once():
    assert main(["--topic", "AI tools"]) == 2


def test_cli_runs_due_jobs_and_returns_success():
    runner = MagicMock()
    runner.run_once.return_value = [{"status": "COMPLETED"}]

    with patch("app.main.AutomationRunner", return_value=runner):
        assert main(["--run-once"]) == 0

    runner.run_once.assert_called_once_with()