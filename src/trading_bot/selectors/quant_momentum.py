from __future__ import annotations

from dataclasses import dataclass

from trading_bot.models.market import CandidateScore, DailyBar
from trading_bot.selectors.base import PriceUniverse


@dataclass
class MomentumSelector:
    """단기/중기 모멘텀과 유동성을 조합한 단순 퀀트 종목 셀렉터."""

    min_history: int = 60
    min_avg_turnover: float = 100_000_000
    weight_m20: float = 0.35
    weight_m60: float = 0.45
    weight_volatility: float = 0.2

    def select(self, universe: PriceUniverse, top_n: int = 10) -> list[CandidateScore]:
        scored: list[CandidateScore] = []
        for symbol, bars in universe.items():
            if len(bars) < self.min_history:
                continue

            closes = [bar.close for bar in bars]
            vols = [bar.volume for bar in bars]
            turnover20 = sum(c * v for c, v in zip(closes[-20:], vols[-20:])) / 20
            if turnover20 < self.min_avg_turnover:
                continue

            m20 = _return_ratio(closes, 20)
            m60 = _return_ratio(closes, 60)
            vol20 = _volatility(closes[-20:])

            # 변동성은 낮을수록 점수 상승하도록 역부호 처리
            score = (
                self.weight_m20 * m20
                + self.weight_m60 * m60
                - self.weight_volatility * vol20
            )

            reason = (
                f"m20={m20:.4f}, m60={m60:.4f}, vol20={vol20:.4f}, "
                f"turnover20={turnover20:,.0f}"
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
    return var ** 0.5
