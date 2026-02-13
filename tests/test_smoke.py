from trading_bot.main import main


def test_main_runs(capsys):
    main()
    captured = capsys.readouterr()
    assert "백테스트 데모" in captured.out
    assert "total_return=" in captured.out
