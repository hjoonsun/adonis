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
    """일봉 기반 스윙 전략(진입/청산/손절/익절 세분화)."""

    fast_window: int = 20
    slow_window: int = 60

    # 진입 규칙
    entry_buffer: float = 0.002
    momentum_lookback: int = 5
    cooldown_days: int = 3

    # 청산/리스크 규칙
    stop_loss: float = -0.07
    take_profit: float = 0.15
    trailing_stop: float = 0.06
    max_holding_days: int = 40

    def decide(
        self,
        symbol: str,
        bars: list[DailyBar],
        in_position: bool,
        entry_price: float | None = None,
        highest_price_since_entry: float | None = None,
        holding_days: int = 0,
        cooldown_remaining: int = 0,
    ) -> StrategyDecision:
        min_len = max(self.fast_window, self.slow_window, self.momentum_lookback + 1)
        if len(bars) < min_len:
            return StrategyDecision(symbol, Signal.HOLD, "데이터 부족")

        closes = [b.close for b in bars]
        latest = closes[-1]
        ma_fast = _sma(closes, self.fast_window)
        ma_slow = _sma(closes, self.slow_window)
        ma_fast_prev = _sma(closes[:-1], self.fast_window)
        momentum_n = _return_ratio(closes, self.momentum_lookback)

        if in_position and entry_price:
            pnl = (latest / entry_price) - 1.0
            peak = highest_price_since_entry or latest
            drawdown_from_peak = (latest / peak) - 1.0 if peak > 0 else 0.0

            if pnl <= self.stop_loss:
                return StrategyDecision(symbol, Signal.SELL, f"손절 조건 충족({pnl:.2%})")

            if drawdown_from_peak <= -self.trailing_stop:
                return StrategyDecision(symbol, Signal.SELL, f"트레일링 스탑({drawdown_from_peak:.2%})")

            if holding_days >= self.max_holding_days:
                return StrategyDecision(symbol, Signal.SELL, f"보유기간 초과({holding_days}일)")

            if pnl >= self.take_profit and latest < ma_fast:
                return StrategyDecision(symbol, Signal.SELL, f"익절 후 약세 전환({pnl:.2%})")

            if ma_fast < ma_slow:
                return StrategyDecision(symbol, Signal.SELL, "추세 이탈")

        if not in_position:
            if cooldown_remaining > 0:
                return StrategyDecision(symbol, Signal.HOLD, f"쿨다운({cooldown_remaining}일)")

            trend_ok = ma_fast > ma_slow and latest > ma_fast * (1 + self.entry_buffer)
            acceleration_ok = ma_fast >= ma_fast_prev
            momentum_ok = momentum_n > 0

            if trend_ok and acceleration_ok and momentum_ok:
                return StrategyDecision(symbol, Signal.BUY, "상승 추세 + 모멘텀 진입")

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


def _return_ratio(closes: list[float], lookback: int) -> float:
    start = closes[-lookback]
    end = closes[-1]
    if start <= 0:
        return 0.0
    return (end / start) - 1.0
