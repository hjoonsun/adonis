from __future__ import annotations

from dataclasses import dataclass
from math import floor

from trading_bot.models.market import DailyBar
from trading_bot.selectors.quant_momentum import MomentumSelector
from trading_bot.strategies.quant_swing import QuantDailyRebalanceStrategy, QuantSwingStrategy, Signal


@dataclass(frozen=True)
class Trade:
    day: str
    symbol: str
    side: str
    price: float
    qty: int
    reason: str


@dataclass(frozen=True)
class EquityPoint:
    day: str
    equity: float
    cash: float


@dataclass(frozen=True)
class BacktestMetrics:
    total_return: float
    max_drawdown: float


@dataclass(frozen=True)
class BacktestResult:
    trades: list[Trade]
    equity_curve: list[EquityPoint]
    metrics: BacktestMetrics


@dataclass
class Position:
    qty: int
    entry_price: float


@dataclass
class SwingBacktestEngine:
    selector: MomentumSelector
    swing: QuantSwingStrategy
    rebalance: QuantDailyRebalanceStrategy
    initial_cash: float = 10_000_000

    def run(self, universe: dict[str, list[DailyBar]]) -> BacktestResult:
        symbols = sorted(universe.keys())
        if not symbols:
            return BacktestResult([], [], BacktestMetrics(0.0, 0.0))

        length = min(len(universe[s]) for s in symbols)
        min_history = getattr(self.selector, "filters", None).min_history if getattr(self.selector, "filters", None) else 60
        start_i = max(min_history, self.swing.slow_window)

        cash = self.initial_cash
        positions: dict[str, Position] = {}
        trades: list[Trade] = []
        equity_curve: list[EquityPoint] = []

        for i in range(start_i, length):
            day = universe[symbols[0]][i].day.isoformat()
            history = {s: universe[s][: i + 1] for s in symbols}

            # 1) 보유 종목의 전략 청산 신호 먼저 확인
            for symbol in list(positions.keys()):
                bars = history[symbol]
                close = bars[-1].close
                decision = self.swing.decide(
                    symbol,
                    bars,
                    in_position=True,
                    entry_price=positions[symbol].entry_price,
                )
                if decision.signal == Signal.SELL:
                    pos = positions.pop(symbol)
                    cash += pos.qty * close
                    trades.append(Trade(day, symbol, "SELL", close, pos.qty, decision.reason))

            # 2) 랭킹 선정 + 리밸런싱
            ranked = self.selector.select(history, top_n=max(self.rebalance.hold_top_n, 10))
            ranked_symbols = [r.symbol for r in ranked]
            to_buy, to_sell = self.rebalance.rebalance_targets(ranked_symbols, set(positions))

            for symbol in sorted(to_sell):
                if symbol not in positions:
                    continue
                close = history[symbol][-1].close
                pos = positions.pop(symbol)
                cash += pos.qty * close
                trades.append(Trade(day, symbol, "SELL", close, pos.qty, "리밸런싱 제외"))

            buy_candidates = []
            for symbol in ranked_symbols:
                if symbol not in to_buy:
                    continue
                decision = self.swing.decide(symbol, history[symbol], in_position=False)
                if decision.signal == Signal.BUY:
                    buy_candidates.append((symbol, decision.reason))

            slots = len(buy_candidates)
            if slots > 0:
                budget_per_trade = cash / slots
                for symbol, reason in buy_candidates:
                    close = history[symbol][-1].close
                    qty = floor(budget_per_trade / close)
                    if qty <= 0:
                        continue
                    cost = qty * close
                    if cost > cash:
                        continue
                    cash -= cost
                    positions[symbol] = Position(qty=qty, entry_price=close)
                    trades.append(Trade(day, symbol, "BUY", close, qty, reason))

            # 3) 일별 자산 기록
            holdings_value = sum(
                positions[s].qty * history[s][-1].close for s in positions
            )
            equity_curve.append(EquityPoint(day=day, equity=cash + holdings_value, cash=cash))

        metrics = _calc_metrics(self.initial_cash, equity_curve)
        return BacktestResult(trades=trades, equity_curve=equity_curve, metrics=metrics)


def _calc_metrics(initial_cash: float, equity_curve: list[EquityPoint]) -> BacktestMetrics:
    if not equity_curve:
        return BacktestMetrics(total_return=0.0, max_drawdown=0.0)

    total_return = (equity_curve[-1].equity / initial_cash) - 1.0

    peak = equity_curve[0].equity
    max_dd = 0.0
    for p in equity_curve:
        if p.equity > peak:
            peak = p.equity
        dd = (p.equity / peak) - 1.0
        if dd < max_dd:
            max_dd = dd

    return BacktestMetrics(total_return=total_return, max_drawdown=max_dd)
