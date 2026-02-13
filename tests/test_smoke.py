from trading_bot.main import main


def test_main_runs(capsys):
    main()
    captured = capsys.readouterr()
    assert "실전형 백테스트 데모" in captured.out
    assert "csv=" in captured.out
    assert "batch_scenarios=" in captured.out
