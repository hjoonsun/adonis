from __future__ import annotations

from dataclasses import dataclass

from trading_bot.models.market import CandidateScore
from trading_bot.selectors.base import PriceUniverse


@dataclass(frozen=True)
class MomentumFilterConfig:
    """하드 필터 규칙."""

    min_history: int = 60
    min_avg_turnover: float = 100_000_000
    min_price: float = 1_000
    max_volatility20: float = 0.08
    min_m20: float = -0.2
    min_m60: float = -0.3


@dataclass(frozen=True)
class MomentumScoreConfig:
    """스코어링 가중치."""

    weight_m20: float = 0.35
    weight_m60: float = 0.45
    weight_volatility: float = 0.2
    weight_turnover: float = 0.1


@dataclass
class MomentumSelector:
    """필터/점수 파라미터를 외부에서 조정할 수 있는 모멘텀 셀렉터."""

    filters: MomentumFilterConfig = MomentumFilterConfig()
    score: MomentumScoreConfig = MomentumScoreConfig()

    def select(self, universe: PriceUniverse, top_n: int = 10) -> list[CandidateScore]:
        scored: list[CandidateScore] = []
        for symbol, bars in universe.items():
            if len(bars) < self.filters.min_history:
                continue

            closes = [bar.close for bar in bars]
            vols = [bar.volume for bar in bars]
            latest = closes[-1]

            m20 = _return_ratio(closes, 20)
            m60 = _return_ratio(closes, 60)
            vol20 = _volatility(closes[-20:])
            turnover20 = sum(c * v for c, v in zip(closes[-20:], vols[-20:])) / 20

            if latest < self.filters.min_price:
                continue
            if turnover20 < self.filters.min_avg_turnover:
                continue
            if vol20 > self.filters.max_volatility20:
                continue
            if m20 < self.filters.min_m20 or m60 < self.filters.min_m60:
                continue

            score = (
                self.score.weight_m20 * m20
                + self.score.weight_m60 * m60
                - self.score.weight_volatility * vol20
                + self.score.weight_turnover * _safe_log10(turnover20)
            )

            reason = (
                f"m20={m20:.4f}, m60={m60:.4f}, vol20={vol20:.4f}, "
                f"turnover20={turnover20:,.0f}, px={latest:.0f}"
            )
            scored.append(CandidateScore(symbol=symbol, score=score, reason=reason))

        return sorted(scored, key=lambda x: x.score, reverse=True)[:top_n]


def _return_ratio(closes: list[float], lookback: int) -> float:
    start = closes[-lookback]
    end = closes[-1]
    if start <= 0:
        return 0.0
    return (end / start) - 1.0


def _volatility(closes: list[float]) -> float:
    if len(closes) < 2:
        return 0.0

    returns: list[float] = []
    for prev, curr in zip(closes[:-1], closes[1:]):
        if prev <= 0:
            continue
        returns.append((curr / prev) - 1.0)

    if not returns:
        return 0.0

    mean = sum(returns) / len(returns)
    var = sum((r - mean) ** 2 for r in returns) / len(returns)
    return var**0.5


def _safe_log10(x: float) -> float:
    if x <= 0:
        return 0.0
    # import를 try/catch로 감싸지 않기 위한 로컬 지연 import
    from math import log10

    return log10(x)
