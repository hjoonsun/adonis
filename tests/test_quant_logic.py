from datetime import date, timedelta

from trading_bot.models.market import DailyBar
from trading_bot.selectors.quant_momentum import MomentumFilterConfig, MomentumScoreConfig, MomentumSelector
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
    selector = MomentumSelector(filters=MomentumFilterConfig(min_avg_turnover=1, min_price=1))
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


def test_momentum_selector_filters_out_low_price_stock():
    selector = MomentumSelector(
        filters=MomentumFilterConfig(min_avg_turnover=1, min_price=5_000)
    )
    universe = {
        "LOW": make_bars(100, 0.003),
        "HIGH": make_bars(10_000, 0.001),
    }

    selected = selector.select(universe, top_n=5)
    assert all(item.symbol != "LOW" for item in selected)


def test_momentum_selector_score_weights_are_customizable():
    universe = {
        "FAST": make_bars(100, 0.0025),
        "STABLE": make_bars(100, 0.0012),
    }

    default_selector = MomentumSelector(
        filters=MomentumFilterConfig(min_avg_turnover=1, min_price=1)
    )
    conservative_selector = MomentumSelector(
        filters=MomentumFilterConfig(min_avg_turnover=1, min_price=1),
        score=MomentumScoreConfig(weight_m20=0.1, weight_m60=0.2, weight_volatility=1.2, weight_turnover=0.0),
    )

    default_scored = default_selector.select(universe, top_n=2)
    conservative_scored = conservative_selector.select(universe, top_n=2)

    assert len(default_scored) == 2
    assert len(conservative_scored) == 2
    assert default_scored[0].score != conservative_scored[0].score
