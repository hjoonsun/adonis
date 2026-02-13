"""자동매매 프로젝트 엔트리포인트."""

from __future__ import annotations

from datetime import date, timedelta

from trading_bot.backtesting.engine import BacktestExecutionConfig, SwingBacktestEngine
from trading_bot.core.risk_manager import RiskConfig, RiskManager
from trading_bot.backtesting.report import export_backtest_csv
from trading_bot.models.market import DailyBar
from trading_bot.selectors.quant_momentum import MomentumSelector
from trading_bot.strategies.quant_swing import QuantDailyRebalanceStrategy, QuantSwingStrategy


def _mock_bars(base: float, drift: float, symbol_seed: int) -> list[DailyBar]:
    bars: list[DailyBar] = []
    start = date(2025, 7, 1)
    price = base
    for i in range(184):
        noise = ((i + symbol_seed) % 7 - 3) * 0.002
        price = price * (1 + drift + noise)
        bars.append(
            DailyBar(
                day=start + timedelta(days=i),
                open=price * 0.99,
                high=price * 1.01,
                low=price * 0.98,
                close=price,
                volume=1_000_000 + (i * 1_000),
            )
        )
    return bars


def main() -> None:
    universe = {
        "005930": _mock_bars(70000, 0.0015, 1),
        "000660": _mock_bars(120000, 0.0012, 2),
        "035420": _mock_bars(180000, 0.0007, 3),
    }

    engine = SwingBacktestEngine(
        selector=MomentumSelector(),
        swing=QuantSwingStrategy(),
        rebalance=QuantDailyRebalanceStrategy(hold_top_n=2),
        risk=RiskManager(RiskConfig()),
        execution=BacktestExecutionConfig(
            commission_rate=0.00015,
            sell_tax_rate=0.0018,
            slippage_bps=5,
            allow_weekend_trading=False,
        ),
    )
    result = engine.run(universe)
    trades_csv, equity_csv = export_backtest_csv(result)

    print("api 를 이용한 주식 자동매매 V1.0 - 실전형 백테스트 데모")
    print(f"trades={len(result.trades)}")
    print(f"total_return={result.metrics.total_return:.2%}")
    print(f"max_drawdown={result.metrics.max_drawdown:.2%}")
    print(f"cagr={result.metrics.cagr:.2%}, sharpe={result.metrics.sharpe:.2f}")
    print(f"win_rate={result.metrics.win_rate:.2%}, profit_factor={result.metrics.profit_factor:.2f}")
    print(f"csv={trades_csv}, {equity_csv}")


if __name__ == "__main__":
    main()
