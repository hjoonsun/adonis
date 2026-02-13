from datetime import date, timedelta

from trading_bot.backtesting.engine import BacktestExecutionConfig, SwingBacktestEngine
from trading_bot.core.risk_manager import RiskConfig, RiskManager
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
        risk=RiskManager(RiskConfig()),
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
        risk=RiskManager(RiskConfig()),
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
        swing=QuantSwingStrategy(entry_buffer=0.0),
        rebalance=QuantDailyRebalanceStrategy(hold_top_n=1),
        risk=RiskManager(RiskConfig(max_position_weight=1.0)),
        execution=BacktestExecutionConfig(commission_rate=0.0, sell_tax_rate=0.0, slippage_bps=0.0),
    ).run(universe)

    costly = SwingBacktestEngine(
        selector=MomentumSelector(filters=MomentumFilterConfig(min_avg_turnover=1, min_price=1)),
        swing=QuantSwingStrategy(entry_buffer=0.0),
        rebalance=QuantDailyRebalanceStrategy(hold_top_n=1),
        risk=RiskManager(RiskConfig(max_position_weight=1.0)),
        execution=BacktestExecutionConfig(commission_rate=0.002, sell_tax_rate=0.003, slippage_bps=20.0),
    ).run(universe)

    assert costly.metrics.total_return < base.metrics.total_return


def test_metrics_extended_fields_exist():
    universe = {
        "A": make_bars(100, 0.002),
        "B": make_bars(100, 0.001),
        "C": make_bars(100, -0.0007),
    }
    result = SwingBacktestEngine(
        selector=MomentumSelector(filters=MomentumFilterConfig(min_avg_turnover=1, min_price=1)),
        swing=QuantSwingStrategy(),
        rebalance=QuantDailyRebalanceStrategy(hold_top_n=2),
        risk=RiskManager(RiskConfig()),
    ).run(universe)

    assert -1.0 <= result.metrics.max_drawdown <= 0.0
    assert result.metrics.cagr == result.metrics.cagr
    assert result.metrics.sharpe == result.metrics.sharpe
    assert 0.0 <= result.metrics.win_rate <= 1.0
    assert result.metrics.profit_factor >= 0.0


def test_risk_manager_limits_position_count():
    universe = {
        "A": make_bars(100, 0.003),
        "B": make_bars(100, 0.003),
        "C": make_bars(100, 0.003),
        "D": make_bars(100, 0.003),
    }
    engine = SwingBacktestEngine(
        selector=MomentumSelector(filters=MomentumFilterConfig(min_avg_turnover=1, min_price=1)),
        swing=QuantSwingStrategy(entry_buffer=0.0),
        rebalance=QuantDailyRebalanceStrategy(hold_top_n=4),
        risk=RiskManager(RiskConfig(max_positions=1, max_position_weight=1.0)),
    )
    result = engine.run(universe)

    buy_count_same_day = {}
    for t in result.trades:
        if t.side != "BUY":
            continue
        buy_count_same_day[t.day] = buy_count_same_day.get(t.day, 0) + 1

    assert all(count <= 1 for count in buy_count_same_day.values())
