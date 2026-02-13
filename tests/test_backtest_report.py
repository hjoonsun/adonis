from datetime import date, timedelta

from trading_bot.backtesting.engine import SwingBacktestEngine
from trading_bot.core.risk_manager import RiskConfig, RiskManager
from trading_bot.backtesting.automation import BatchResultRow
from trading_bot.backtesting.report import export_backtest_csv, export_batch_summary_csv
from trading_bot.models.market import DailyBar
from trading_bot.selectors.quant_momentum import MomentumFilterConfig, MomentumSelector
from trading_bot.strategies.quant_swing import QuantDailyRebalanceStrategy, QuantSwingStrategy


def make_bars(start_price: float, daily_return: float, days: int = 120) -> list[DailyBar]:
    items = []
    price = start_price
    start = date(2024, 1, 1)
    for i in range(days):
        price *= 1 + daily_return
        items.append(
            DailyBar(
                day=start + timedelta(days=i),
                open=price,
                high=price,
                low=price,
                close=price,
                volume=2_000_000,
            )
        )
    return items


def test_export_backtest_csv_creates_files(tmp_path):
    universe = {
        "A": make_bars(100, 0.002),
        "B": make_bars(100, 0.001),
    }
    engine = SwingBacktestEngine(
        selector=MomentumSelector(filters=MomentumFilterConfig(min_avg_turnover=1, min_price=1)),
        swing=QuantSwingStrategy(),
        rebalance=QuantDailyRebalanceStrategy(hold_top_n=1),
        risk=RiskManager(RiskConfig()),
    )
    result = engine.run(universe)

    trades_path, equity_path = export_backtest_csv(result, output_dir=str(tmp_path))

    assert (tmp_path / "trades.csv").exists()
    assert (tmp_path / "equity_curve.csv").exists()
    assert trades_path.endswith("trades.csv")
    assert equity_path.endswith("equity_curve.csv")



def test_export_batch_summary_csv_creates_file(tmp_path):
    rows = [
        BatchResultRow("s1", 0.1, 0.2, -0.05, 1.2, 0.55, 1.8, 12),
        BatchResultRow("s2", -0.02, -0.03, -0.1, -0.2, 0.45, 0.8, 8),
    ]
    path = export_batch_summary_csv(rows, output_dir=str(tmp_path))
    assert (tmp_path / "batch_summary.csv").exists()
    assert path.endswith("batch_summary.csv")
