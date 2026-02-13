from trading_bot.core.risk_manager import RiskConfig, RiskManager


def test_risk_manager_blocks_by_weight():
    rm = RiskManager(RiskConfig(max_position_weight=0.2))
    allowed = rm.allows_new_position(
        current_positions=0,
        proposed_cost=300,
        equity=1_000,
        day_start_equity=1_000,
        current_equity=1_000,
    )
    assert allowed is False


def test_risk_manager_blocks_by_daily_loss_limit():
    rm = RiskManager(RiskConfig(daily_loss_limit=-0.02, max_position_weight=1.0))
    allowed = rm.allows_new_position(
        current_positions=0,
        proposed_cost=100,
        equity=900,
        day_start_equity=1_000,
        current_equity=970,
    )
    assert allowed is False
