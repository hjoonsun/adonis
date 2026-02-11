from __future__ import annotations

from typing import Protocol

from trading_bot.models.market import CandidateScore, DailyBar


PriceUniverse = dict[str, list[DailyBar]]


class StockSelector(Protocol):
    """종목 탐색/선정 로직을 교체 가능한 형태로 정의."""

    def select(self, universe: PriceUniverse, top_n: int = 10) -> list[CandidateScore]:
        ...
