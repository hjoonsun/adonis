"""자동매매 프로젝트 엔트리포인트."""

from __future__ import annotations

from datetime import date, timedelta

from trading_bot.backtesting.engine import SwingBacktestEngine
from trading_bot.models.market import DailyBar
from trading_bot.selectors.quant_momentum import MomentumSelector
from trading_bot.strategies.quant_swing import QuantDailyRebalanceStrategy, QuantSwingStrategy


def _mock_bars(base: float, drift: float, symbol_seed: int) -> list[DailyBar]:
    bars: list[DailyBar] = []
    start = date(2024, 1, 1)
    price = base
    for i in range(120):
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
    )
    result = engine.run(universe)

    print("api 를 이용한 주식 자동매매 V1.0 - 백테스트 데모")
    print(f"trades={len(result.trades)}")
    print(f"total_return={result.metrics.total_return:.2%}")
    print(f"max_drawdown={result.metrics.max_drawdown:.2%}")


if __name__ == "__main__":
    main()
