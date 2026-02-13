from __future__ import annotations

import csv
from pathlib import Path

from trading_bot.backtesting.engine import BacktestResult


def export_backtest_csv(result: BacktestResult, output_dir: str = "artifacts") -> tuple[str, str]:
    base = Path(output_dir)
    base.mkdir(parents=True, exist_ok=True)

    trades_path = base / "trades.csv"
    with trades_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["day", "symbol", "side", "price", "qty", "fee", "reason"])
        for t in result.trades:
            writer.writerow([t.day, t.symbol, t.side, f"{t.price:.4f}", t.qty, f"{t.fee:.4f}", t.reason])

    equity_path = base / "equity_curve.csv"
    with equity_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["day", "equity", "cash"])
        for p in result.equity_curve:
            writer.writerow([p.day, f"{p.equity:.4f}", f"{p.cash:.4f}"])

    return str(trades_path), str(equity_path)
