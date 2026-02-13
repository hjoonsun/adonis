from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DailyBar:
    """일봉 데이터 1개."""

    day: date
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class CandidateScore:
    """종목 선정 결과."""

    symbol: str
    score: float
    reason: str
