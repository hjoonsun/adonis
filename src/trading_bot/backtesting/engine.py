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
    fee: float = 0.0


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


@dataclass(frozen=True)
class BacktestExecutionConfig:
    commission_rate: float = 0.00015
    sell_tax_rate: float = 0.0018
    slippage_bps: float = 5.0
    allow_weekend_trading: bool = False


@dataclass
class Position:
    qty: int
    entry_price: float
    highest_price: float
    holding_days: int = 0


@dataclass
class SwingBacktestEngine:
    selector: MomentumSelector
    swing: QuantSwingStrategy
    rebalance: QuantDailyRebalanceStrategy
    initial_cash: float = 10_000_000
    execution: BacktestExecutionConfig = BacktestExecutionConfig()

    def run(self, universe: dict[str, list[DailyBar]]) -> BacktestResult:
        symbols = sorted(universe.keys())
        if not symbols:
            return BacktestResult([], [], BacktestMetrics(0.0, 0.0))

        length = min(len(universe[s]) for s in symbols)
        min_history = getattr(self.selector, "filters", None).min_history if getattr(self.selector, "filters", None) else 60
        start_i = max(min_history, self.swing.slow_window)

        cash = self.initial_cash
        positions: dict[str, Position] = {}
        cooldown_until_index: dict[str, int] = {}
        trades: list[Trade] = []
        equity_curve: list[EquityPoint] = []

        for i in range(start_i, length):
            current_day = universe[symbols[0]][i].day
            if (not self.execution.allow_weekend_trading) and current_day.weekday() >= 5:
                continue

            day = current_day.isoformat()
            history = {s: universe[s][: i + 1] for s in symbols}

            for symbol in list(positions.keys()):
                bars = history[symbol]
                raw_close = bars[-1].close
                pos_ref = positions[symbol]
                pos_ref.holding_days += 1
                pos_ref.highest_price = max(pos_ref.highest_price, raw_close)
                decision = self.swing.decide(
                    symbol,
                    bars,
                    in_position=True,
                    entry_price=pos_ref.entry_price,
                    highest_price_since_entry=pos_ref.highest_price,
                    holding_days=pos_ref.holding_days,
                )
                if decision.signal == Signal.SELL:
                    pos = positions.pop(symbol)
                    cooldown_until_index[symbol] = i + self.swing.cooldown_days
                    exec_price = _sell_price(raw_close, self.execution.slippage_bps)
                    gross = pos.qty * exec_price
                    fee = gross * (self.execution.commission_rate + self.execution.sell_tax_rate)
                    cash += gross - fee
                    trades.append(Trade(day, symbol, "SELL", exec_price, pos.qty, decision.reason, fee))

            ranked = self.selector.select(history, top_n=max(self.rebalance.hold_top_n, 10))
            ranked_symbols = [r.symbol for r in ranked]
            to_buy, to_sell = self.rebalance.rebalance_targets(ranked_symbols, set(positions))

            for symbol in sorted(to_sell):
                if symbol not in positions:
                    continue
                raw_close = history[symbol][-1].close
                pos = positions.pop(symbol)
                cooldown_until_index[symbol] = i + self.swing.cooldown_days
                exec_price = _sell_price(raw_close, self.execution.slippage_bps)
                gross = pos.qty * exec_price
                fee = gross * (self.execution.commission_rate + self.execution.sell_tax_rate)
                cash += gross - fee
                trades.append(Trade(day, symbol, "SELL", exec_price, pos.qty, "리밸런싱 제외", fee))

            buy_candidates = []
            for symbol in ranked_symbols:
                if symbol not in to_buy:
                    continue
                cooldown_remaining = max(0, cooldown_until_index.get(symbol, -1) - i)
                decision = self.swing.decide(symbol, history[symbol], in_position=False, cooldown_remaining=cooldown_remaining)
                if decision.signal == Signal.BUY:
                    buy_candidates.append((symbol, decision.reason))

            slots = len(buy_candidates)
            if slots > 0:
                budget_per_trade = cash / slots
                for symbol, reason in buy_candidates:
                    raw_close = history[symbol][-1].close
                    exec_price = _buy_price(raw_close, self.execution.slippage_bps)
                    qty = floor(budget_per_trade / exec_price)
                    if qty <= 0:
                        continue
                    gross = qty * exec_price
                    fee = gross * self.execution.commission_rate
                    total = gross + fee
                    if total > cash:
                        continue
                    cash -= total
                    positions[symbol] = Position(qty=qty, entry_price=exec_price, highest_price=raw_close, holding_days=0)
                    trades.append(Trade(day, symbol, "BUY", exec_price, qty, reason, fee))

            holdings_value = sum(positions[s].qty * history[s][-1].close for s in positions)
            equity_curve.append(EquityPoint(day=day, equity=cash + holdings_value, cash=cash))

        metrics = _calc_metrics(self.initial_cash, equity_curve)
        return BacktestResult(trades=trades, equity_curve=equity_curve, metrics=metrics)


def _buy_price(price: float, slippage_bps: float) -> float:
    return price * (1 + slippage_bps / 10_000)


def _sell_price(price: float, slippage_bps: float) -> float:
    return price * (1 - slippage_bps / 10_000)


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
