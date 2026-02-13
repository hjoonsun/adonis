from trading_bot.backtesting.automation import run_batch_backtests


def test_run_batch_backtests_creates_summary(tmp_path):
    rows, summary = run_batch_backtests(output_dir=str(tmp_path))

    assert len(rows) == 4
    assert (tmp_path / "batch_summary.csv").exists()
    assert summary.endswith("batch_summary.csv")


def test_batch_regression_baseline_threshold(tmp_path):
    rows, _ = run_batch_backtests(output_dir=str(tmp_path))

    avg_return = sum(r.total_return for r in rows) / len(rows)
    # 과도한 성능 붕괴 회귀 방지용 완화 기준선
    assert avg_return > -0.35
