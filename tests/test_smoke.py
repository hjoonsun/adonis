from trading_bot.main import main


def test_main_runs(capsys):
    main()
    captured = capsys.readouterr()
    assert "퀀트 데모" in captured.out
    assert "score=" in captured.out
