from trading_bot.main import main


def test_main_runs(capsys):
    main()
    captured = capsys.readouterr()
    assert "초기 세팅 완료" in captured.out
