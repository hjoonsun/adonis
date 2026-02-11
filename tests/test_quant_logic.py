from datetime import date, timedelta

from trading_bot.models.market import DailyBar
from trading_bot.selectors.quant_momentum import MomentumSelector
from trading_bot.strategies.quant_swing import QuantDailyRebalanceStrategy, QuantSwingStrategy, Signal


def make_bars(start_price: float, daily_return: float, days: int = 80) -> list[DailyBar]:
    items = []
    price = start_price
    d = date(2024, 1, 1)
    for i in range(days):
        price *= 1 + daily_return
        items.append(
            DailyBar(
                day=d + timedelta(days=i),
                open=price,
                high=price,
                low=price,
                close=price,
                volume=2_000_000,
            )
        )
    return items


def test_momentum_selector_ranks_higher_momentum_first():
    selector = MomentumSelector(min_avg_turnover=1)
    universe = {
        "A": make_bars(100, 0.002),
        "B": make_bars(100, 0.0005),
    }

    selected = selector.select(universe, top_n=2)
    assert selected[0].symbol == "A"


def test_quant_swing_buy_signal_on_uptrend():
    strategy = QuantSwingStrategy()
    bars = make_bars(100, 0.002)

    decision = strategy.decide("A", bars, in_position=False)
    assert decision.signal == Signal.BUY


def test_quant_swing_sell_signal_on_stop_loss():
    strategy = QuantSwingStrategy(stop_loss=-0.03)
    bars = make_bars(100, -0.002)

    decision = strategy.decide("A", bars, in_position=True, entry_price=120)
    assert decision.signal == Signal.SELL


def test_daily_rebalance_targets():
    rebalance = QuantDailyRebalanceStrategy(hold_top_n=2)
    buy, sell = rebalance.rebalance_targets(["A", "B", "C"], {"B", "D"})

    assert buy == {"A"}
    assert sell == {"D"}
