from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from trading_bot.backtesting.engine import BacktestExecutionConfig, BacktestResult, SwingBacktestEngine
from trading_bot.backtesting.report import export_batch_summary_csv
from trading_bot.core.risk_manager import RiskConfig, RiskManager
from trading_bot.models.market import DailyBar
from trading_bot.selectors.quant_momentum import MomentumFilterConfig, MomentumSelector
from trading_bot.strategies.quant_swing import QuantDailyRebalanceStrategy, QuantSwingStrategy


@dataclass(frozen=True)
class BatchScenario:
    name: str
    daily_drifts: dict[str, float]


@dataclass(frozen=True)
class BatchResultRow:
    scenario: str
    total_return: float
    cagr: float
    max_drawdown: float
    sharpe: float
    win_rate: float
    profit_factor: float
    trades: int


def generate_mock_universe(
    start: date,
    days: int,
    daily_drifts: dict[str, float],
) -> dict[str, list[DailyBar]]:
    universe: dict[str, list[DailyBar]] = {}
    for seed, (symbol, drift) in enumerate(daily_drifts.items(), start=1):
        price = 100_000.0 + (seed * 1_000)
        bars: list[DailyBar] = []
        for i in range(days):
            day = start + timedelta(days=i)
            noise = ((i + seed) % 9 - 4) * 0.0015
            price = price * (1 + drift + noise)
            bars.append(
                DailyBar(
                    day=day,
                    open=price * 0.995,
                    high=price * 1.008,
                    low=price * 0.992,
                    close=price,
                    volume=1_500_000 + i * 1_200,
                )
            )
        universe[symbol] = bars
    return universe


def run_batch_backtests(output_dir: str = "artifacts") -> tuple[list[BatchResultRow], str]:
    scenarios = [
        BatchScenario("bull", {"005930": 0.0015, "000660": 0.0012, "035420": 0.0009}),
        BatchScenario("sideways", {"005930": 0.0002, "000660": 0.0001, "035420": 0.0000}),
        BatchScenario("bear", {"005930": -0.0007, "000660": -0.0005, "035420": -0.0006}),
        BatchScenario("volatile", {"005930": 0.0005, "000660": -0.0002, "035420": 0.0003}),
    ]

    rows: list[BatchResultRow] = []
    for scenario in scenarios:
        universe = generate_mock_universe(date(2025, 1, 1), 220, scenario.daily_drifts)
        engine = SwingBacktestEngine(
            selector=MomentumSelector(filters=MomentumFilterConfig(min_avg_turnover=1, min_price=1)),
            swing=QuantSwingStrategy(entry_buffer=0.0),
            rebalance=QuantDailyRebalanceStrategy(hold_top_n=2),
            risk=RiskManager(RiskConfig(max_position_weight=1.0)),
            execution=BacktestExecutionConfig(allow_weekend_trading=False),
        )
        result = engine.run(universe)
        rows.append(_to_row(scenario.name, result))

    summary_path = export_batch_summary_csv(rows, output_dir=output_dir)
    return rows, summary_path


def _to_row(name: str, result: BacktestResult) -> BatchResultRow:
    return BatchResultRow(
        scenario=name,
        total_return=result.metrics.total_return,
        cagr=result.metrics.cagr,
        max_drawdown=result.metrics.max_drawdown,
        sharpe=result.metrics.sharpe,
        win_rate=result.metrics.win_rate,
        profit_factor=result.metrics.profit_factor,
        trades=len(result.trades),
    )
