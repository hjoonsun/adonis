from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskConfig:
    max_positions: int = 5
    max_position_weight: float = 0.6
    daily_loss_limit: float = -0.03


@dataclass
class RiskManager:
    config: RiskConfig = RiskConfig()

    def allows_new_position(
        self,
        current_positions: int,
        proposed_cost: float,
        equity: float,
        day_start_equity: float,
        current_equity: float,
    ) -> bool:
        if current_positions >= self.config.max_positions:
            return False
        if equity <= 0:
            return False
        if (proposed_cost / equity) > self.config.max_position_weight:
            return False

        if day_start_equity > 0:
            day_return = (current_equity / day_start_equity) - 1.0
            if day_return <= self.config.daily_loss_limit:
                return False

        return True
