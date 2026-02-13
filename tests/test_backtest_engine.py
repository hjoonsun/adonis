from datetime import date, timedelta

from trading_bot.backtesting.engine import BacktestExecutionConfig, SwingBacktestEngine
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


def test_backtest_engine_runs_and_creates_curve():
    universe = {
        "A": make_bars(100, 0.002),
        "B": make_bars(100, 0.001),
        "C": make_bars(100, -0.0005),
    }

    engine = SwingBacktestEngine(
        selector=MomentumSelector(filters=MomentumFilterConfig(min_avg_turnover=1, min_price=1)),
        swing=QuantSwingStrategy(),
        rebalance=QuantDailyRebalanceStrategy(hold_top_n=2),
        initial_cash=1_000_000,
    )

    result = engine.run(universe)

    assert len(result.equity_curve) > 0
    assert len(result.trades) > 0
    assert result.metrics.total_return != 0
    assert result.metrics.max_drawdown <= 0


def test_backtest_weekend_filter_excludes_weekends():
    universe = {
        "A": make_bars(100, 0.001),
        "B": make_bars(100, 0.0008),
    }
    engine = SwingBacktestEngine(
        selector=MomentumSelector(filters=MomentumFilterConfig(min_avg_turnover=1, min_price=1)),
        swing=QuantSwingStrategy(),
        rebalance=QuantDailyRebalanceStrategy(hold_top_n=1),
        execution=BacktestExecutionConfig(allow_weekend_trading=False),
    )

    result = engine.run(universe)
    for p in result.equity_curve:
        d = date.fromisoformat(p.day)
        assert d.weekday() < 5


def test_execution_costs_reduce_performance():
    universe = {
        "A": make_bars(100, 0.002),
        "B": make_bars(100, 0.001),
    }

    base = SwingBacktestEngine(
        selector=MomentumSelector(filters=MomentumFilterConfig(min_avg_turnover=1, min_price=1)),
        swing=QuantSwingStrategy(),
        rebalance=QuantDailyRebalanceStrategy(hold_top_n=1),
        execution=BacktestExecutionConfig(commission_rate=0.0, sell_tax_rate=0.0, slippage_bps=0.0),
    ).run(universe)

    costly = SwingBacktestEngine(
        selector=MomentumSelector(filters=MomentumFilterConfig(min_avg_turnover=1, min_price=1)),
        swing=QuantSwingStrategy(),
        rebalance=QuantDailyRebalanceStrategy(hold_top_n=1),
        execution=BacktestExecutionConfig(commission_rate=0.002, sell_tax_rate=0.003, slippage_bps=20.0),
    ).run(universe)

    assert costly.metrics.total_return < base.metrics.total_return
