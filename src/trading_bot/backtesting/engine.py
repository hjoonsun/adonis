from __future__ import annotations

from dataclasses import dataclass
from math import floor, sqrt

from trading_bot.core.risk_manager import RiskManager
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
    cagr: float
    max_drawdown: float
    sharpe: float
    win_rate: float
    profit_factor: float


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
    risk: RiskManager
    initial_cash: float = 10_000_000
    execution: BacktestExecutionConfig = BacktestExecutionConfig()

    def run(self, universe: dict[str, list[DailyBar]]) -> BacktestResult:
        symbols = sorted(universe.keys())
        if not symbols:
            return BacktestResult([], [], BacktestMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0))

        length = min(len(universe[s]) for s in symbols)
        min_history = getattr(self.selector, "filters", None).min_history if getattr(self.selector, "filters", None) else 60
        start_i = max(min_history, self.swing.slow_window)

        cash = self.initial_cash
        positions: dict[str, Position] = {}
        cooldown_until_index: dict[str, int] = {}
        trades: list[Trade] = []
        equity_curve: list[EquityPoint] = []
        closed_trade_returns: list[float] = []

        for i in range(start_i, length):
            current_day = universe[symbols[0]][i].day
            if (not self.execution.allow_weekend_trading) and current_day.weekday() >= 5:
                continue

            day = current_day.isoformat()
            history = {s: universe[s][: i + 1] for s in symbols}

            day_start_equity = cash + sum(positions[s].qty * history[s][-1].close for s in positions)

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
                    closed_trade_returns.append((exec_price / pos.entry_price) - 1.0)

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
                closed_trade_returns.append((exec_price / pos.entry_price) - 1.0)

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
                    current_equity = cash + sum(positions[s].qty * history[s][-1].close for s in positions)
                    if not self.risk.allows_new_position(
                        current_positions=len(positions),
                        proposed_cost=total,
                        equity=max(current_equity, 1.0),
                        day_start_equity=day_start_equity,
                        current_equity=current_equity,
                    ):
                        continue
                    if total > cash:
                        continue
                    cash -= total
                    positions[symbol] = Position(qty=qty, entry_price=exec_price, highest_price=raw_close, holding_days=0)
                    trades.append(Trade(day, symbol, "BUY", exec_price, qty, reason, fee))

            holdings_value = sum(positions[s].qty * history[s][-1].close for s in positions)
            equity_curve.append(EquityPoint(day=day, equity=cash + holdings_value, cash=cash))

        metrics = _calc_metrics(self.initial_cash, equity_curve, closed_trade_returns)
        return BacktestResult(trades=trades, equity_curve=equity_curve, metrics=metrics)


def _buy_price(price: float, slippage_bps: float) -> float:
    return price * (1 + slippage_bps / 10_000)


def _sell_price(price: float, slippage_bps: float) -> float:
    return price * (1 - slippage_bps / 10_000)


def _calc_metrics(initial_cash: float, equity_curve: list[EquityPoint], closed_trade_returns: list[float]) -> BacktestMetrics:
    if not equity_curve:
        return BacktestMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    total_return = (equity_curve[-1].equity / initial_cash) - 1.0

    peak = equity_curve[0].equity
    max_dd = 0.0
    for p in equity_curve:
        if p.equity > peak:
            peak = p.equity
        dd = (p.equity / peak) - 1.0
        if dd < max_dd:
            max_dd = dd

    years = max(len(equity_curve) / 252.0, 1e-9)
    cagr = (equity_curve[-1].equity / initial_cash) ** (1 / years) - 1.0

    daily_returns: list[float] = []
    for prev, curr in zip(equity_curve[:-1], equity_curve[1:]):
        if prev.equity <= 0:
            continue
        daily_returns.append((curr.equity / prev.equity) - 1.0)

    sharpe = 0.0
    if daily_returns:
        mean = sum(daily_returns) / len(daily_returns)
        var = sum((r - mean) ** 2 for r in daily_returns) / len(daily_returns)
        std = sqrt(var)
        if std > 0:
            sharpe = (mean / std) * sqrt(252)

    wins = [r for r in closed_trade_returns if r > 0]
    losses = [r for r in closed_trade_returns if r < 0]
    total_closed = len(closed_trade_returns)
    win_rate = (len(wins) / total_closed) if total_closed else 0.0

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0

    return BacktestMetrics(
        total_return=total_return,
        cagr=cagr,
        max_drawdown=max_dd,
        sharpe=sharpe,
        win_rate=win_rate,
        profit_factor=profit_factor,
    )
