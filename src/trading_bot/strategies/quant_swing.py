from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from trading_bot.models.market import DailyBar


class Signal(str, Enum):
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"


@dataclass(frozen=True)
class StrategyDecision:
    symbol: str
    signal: Signal
    reason: str


@dataclass
class QuantSwingStrategy:
    """일봉 기반 스윙 전략(추세 + 단순 리스크 규칙)."""

    fast_window: int = 20
    slow_window: int = 60
    stop_loss: float = -0.07
    take_profit: float = 0.15

    def decide(
        self,
        symbol: str,
        bars: list[DailyBar],
        in_position: bool,
        entry_price: float | None = None,
    ) -> StrategyDecision:
        min_len = max(self.fast_window, self.slow_window)
        if len(bars) < min_len:
            return StrategyDecision(symbol, Signal.HOLD, "데이터 부족")

        closes = [b.close for b in bars]
        ma_fast = _sma(closes, self.fast_window)
        ma_slow = _sma(closes, self.slow_window)
        latest = closes[-1]

        if in_position and entry_price:
            pnl = (latest / entry_price) - 1.0
            if pnl <= self.stop_loss:
                return StrategyDecision(symbol, Signal.SELL, f"손절 조건 충족({pnl:.2%})")
            if pnl >= self.take_profit:
                return StrategyDecision(symbol, Signal.SELL, f"익절 조건 충족({pnl:.2%})")

        if not in_position and ma_fast > ma_slow and latest > ma_fast:
            return StrategyDecision(symbol, Signal.BUY, "상승 추세 진입")

        if in_position and ma_fast < ma_slow:
            return StrategyDecision(symbol, Signal.SELL, "추세 이탈")

        return StrategyDecision(symbol, Signal.HOLD, "조건 미충족")


@dataclass
class QuantDailyRebalanceStrategy:
    """일봉 단위 리밸런싱 전략: 상위 N 종목만 보유."""

    hold_top_n: int = 5

    def rebalance_targets(self, ranked_symbols: list[str], current_positions: set[str]) -> tuple[set[str], set[str]]:
        target = set(ranked_symbols[: self.hold_top_n])
        to_buy = target - current_positions
        to_sell = current_positions - target
        return to_buy, to_sell


def _sma(values: list[float], window: int) -> float:
    section = values[-window:]
    return sum(section) / len(section)
