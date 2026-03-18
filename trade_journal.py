#!/usr/bin/env python3
"""Trade Journal — Typer+Rich CLI for trade performance analysis."""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

app = typer.Typer(
    name="trade-journal",
    help="Crypto trade performance analyzer and journal tool.",
    no_args_is_help=True,
)
console = Console()


def _parse_csv(path: str) -> list[dict]:
    """Parse a trade journal CSV file into a list of trade dicts.

    Expected columns: date, symbol, side, entry_price, exit_price, quantity, pnl, fees
    """
    p = Path(path)
    if not p.exists():
        console.print(f"[red]File not found: {path}[/red]")
        raise typer.Exit(1)
    trades = []
    with open(p, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                trades.append(
                    {
                        "date": datetime.strptime(row["date"].strip(), "%Y-%m-%d"),
                        "symbol": row["symbol"].strip(),
                        "side": row["side"].strip().upper(),
                        "entry_price": float(row["entry_price"]),
                        "exit_price": float(row["exit_price"]),
                        "quantity": float(row["quantity"]),
                        "pnl": float(row["pnl"]),
                        "fees": float(row["fees"]),
                    }
                )
            except (KeyError, ValueError) as e:
                console.print(f"[yellow]Skipping invalid row: {e}[/yellow]")
    if not trades:
        console.print("[red]No valid trades found in CSV.[/red]")
        raise typer.Exit(1)
    trades.sort(key=lambda t: t["date"])
    return trades


def _compute_metrics(trades: list[dict]) -> dict:
    """Compute all performance metrics from a list of trades."""
    total_trades = len(trades)
    net_pnls = [t["pnl"] - t["fees"] for t in trades]
    wins = [p for p in net_pnls if p > 0]
    losses = [p for p in net_pnls if p <= 0]

    win_count = len(wins)
    loss_count = len(losses)
    win_rate = win_count / total_trades * 100 if total_trades > 0 else 0

    total_pnl = sum(net_pnls)
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = sum(losses) / len(losses) if losses else 0
    largest_win = max(wins) if wins else 0
    largest_loss = min(losses) if losses else 0

    # Max consecutive wins/losses
    max_consec_wins = 0
    max_consec_losses = 0
    curr_wins = 0
    curr_losses = 0
    for p in net_pnls:
        if p > 0:
            curr_wins += 1
            curr_losses = 0
            max_consec_wins = max(max_consec_wins, curr_wins)
        else:
            curr_losses += 1
            curr_wins = 0
            max_consec_losses = max(max_consec_losses, curr_losses)

    # Sharpe ratio (daily returns assumed, annualized)
    if len(net_pnls) > 1:
        mean_ret = sum(net_pnls) / len(net_pnls)
        variance = sum((p - mean_ret) ** 2 for p in net_pnls) / (len(net_pnls) - 1)
        std_ret = math.sqrt(variance)
        sharpe = (mean_ret / std_ret * math.sqrt(365)) if std_ret > 0 else 0
    else:
        sharpe = 0

    # Max drawdown
    equity = []
    running = 0.0
    for p in net_pnls:
        running += p
        equity.append(running)

    max_dd = 0.0
    peak = 0.0
    peak_date = trades[0]["date"]
    trough_date = trades[0]["date"]
    dd_peak_date = trades[0]["date"]
    dd_trough_date = trades[0]["date"]
    for i, eq in enumerate(equity):
        if eq > peak:
            peak = eq
            peak_date = trades[i]["date"]
        dd = peak - eq
        if dd > max_dd:
            max_dd = dd
            dd_peak_date = peak_date
            dd_trough_date = trades[i]["date"]

    # R-multiples (risk = |entry - exit| for losses, normalized)
    avg_risk = abs(avg_loss) if avg_loss != 0 else 1
    r_multiples = [p / avg_risk for p in net_pnls]

    # Monthly breakdown
    monthly: dict[str, dict] = {}
    for t, p in zip(trades, net_pnls):
        key = t["date"].strftime("%Y-%m")
        if key not in monthly:
            monthly[key] = {"trades": 0, "pnl": 0.0, "wins": 0}
        monthly[key]["trades"] += 1
        monthly[key]["pnl"] += p
        if p > 0:
            monthly[key]["wins"] += 1

    # By symbol
    by_symbol: dict[str, dict] = {}
    for t, p in zip(trades, net_pnls):
        sym = t["symbol"]
        if sym not in by_symbol:
            by_symbol[sym] = {"trades": 0, "pnl": 0.0, "wins": 0}
        by_symbol[sym]["trades"] += 1
        by_symbol[sym]["pnl"] += p
        if p > 0:
            by_symbol[sym]["wins"] += 1

    # By side
    by_side: dict[str, dict] = {}
    for t, p in zip(trades, net_pnls):
        side = t["side"]
        if side not in by_side:
            by_side[side] = {"trades": 0, "pnl": 0.0, "wins": 0}
        by_side[side]["trades"] += 1
        by_side[side]["pnl"] += p
        if p > 0:
            by_side[side]["wins"] += 1

    # By day of week
    by_dow: dict[str, dict] = {}
    for t, p in zip(trades, net_pnls):
        dow = t["date"].strftime("%A")
        if dow not in by_dow:
            by_dow[dow] = {"trades": 0, "pnl": 0.0, "wins": 0}
        by_dow[dow]["trades"] += 1
        by_dow[dow]["pnl"] += p
        if p > 0:
            by_dow[dow]["wins"] += 1

    # Average trade duration (days between consecutive trades as proxy)
    if len(trades) > 1:
        durations = [
            (trades[i + 1]["date"] - trades[i]["date"]).days
            for i in range(len(trades) - 1)
        ]
        avg_duration = sum(durations) / len(durations)
    else:
        avg_duration = 0

    return {
        "total_trades": total_trades,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "total_pnl": total_pnl,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "largest_win": largest_win,
        "largest_loss": largest_loss,
        "max_consec_wins": max_consec_wins,
        "max_consec_losses": max_consec_losses,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "dd_peak_date": dd_peak_date,
        "dd_trough_date": dd_trough_date,
        "avg_duration_days": avg_duration,
        "r_multiples": r_multiples,
        "monthly": monthly,
        "by_symbol": by_symbol,
        "by_side": by_side,
        "by_dow": by_dow,
        "equity": equity,
        "net_pnls": net_pnls,
        "trades": trades,
    }


def _print_metrics_dashboard(m: dict) -> None:
    """Print a full Rich dashboard of trade metrics."""
    # Summary panel
    pf_str = f"{m['profit_factor']:.2f}" if m["profit_factor"] != float("inf") else "∞"
    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="bold")
    summary.add_column(justify="right")
    summary.add_row("Total Trades", str(m["total_trades"]))
    summary.add_row("Win Rate", f"{m['win_rate']:.1f}%")
    summary.add_row("Profit Factor", pf_str)
    pnl_color = "green" if m["total_pnl"] >= 0 else "red"
    summary.add_row("Total P&L", f"[{pnl_color}]${m['total_pnl']:,.2f}[/{pnl_color}]")
    summary.add_row("Average Win", f"[green]${m['avg_win']:,.2f}[/green]")
    summary.add_row("Average Loss", f"[red]${m['avg_loss']:,.2f}[/red]")
    summary.add_row("Largest Win", f"[green]${m['largest_win']:,.2f}[/green]")
    summary.add_row("Largest Loss", f"[red]${m['largest_loss']:,.2f}[/red]")
    summary.add_row("Max Consecutive Wins", str(m["max_consec_wins"]))
    summary.add_row("Max Consecutive Losses", str(m["max_consec_losses"]))
    summary.add_row("Sharpe Ratio", f"{m['sharpe']:.2f}")
    summary.add_row(
        "Max Drawdown",
        f"[red]${m['max_drawdown']:,.2f}[/red] ({m['dd_peak_date'].strftime('%Y-%m-%d')} → {m['dd_trough_date'].strftime('%Y-%m-%d')})",
    )
    summary.add_row("Avg Trade Spacing", f"{m['avg_duration_days']:.1f} days")
    console.print(Panel(summary, title="Trade Performance Summary", border_style="blue"))

    # R-multiple distribution
    r_mults = m["r_multiples"]
    r_bins = {"< -2R": 0, "-2R to -1R": 0, "-1R to 0R": 0, "0R to 1R": 0, "1R to 2R": 0, "> 2R": 0}
    for r in r_mults:
        if r < -2:
            r_bins["< -2R"] += 1
        elif r < -1:
            r_bins["-2R to -1R"] += 1
        elif r < 0:
            r_bins["-1R to 0R"] += 1
        elif r < 1:
            r_bins["0R to 1R"] += 1
        elif r < 2:
            r_bins["1R to 2R"] += 1
        else:
            r_bins["> 2R"] += 1

    r_table = Table(title="R-Multiple Distribution")
    r_table.add_column("Range")
    r_table.add_column("Count", justify="right")
    r_table.add_column("Bar")
    max_count = max(r_bins.values()) if r_bins else 1
    for rng, cnt in r_bins.items():
        bar_len = int(cnt / max_count * 20) if max_count > 0 else 0
        color = "red" if rng.startswith("<") or rng.startswith("-") else "green"
        r_table.add_row(rng, str(cnt), f"[{color}]{'█' * bar_len}[/{color}]")
    console.print(r_table)

    # Monthly breakdown
    monthly_table = Table(title="Monthly Breakdown")
    monthly_table.add_column("Month")
    monthly_table.add_column("Trades", justify="right")
    monthly_table.add_column("Win Rate", justify="right")
    monthly_table.add_column("P&L", justify="right")
    for month in sorted(m["monthly"].keys()):
        data = m["monthly"][month]
        wr = data["wins"] / data["trades"] * 100 if data["trades"] > 0 else 0
        pnl_color = "green" if data["pnl"] >= 0 else "red"
        monthly_table.add_row(
            month,
            str(data["trades"]),
            f"{wr:.0f}%",
            f"[{pnl_color}]${data['pnl']:,.2f}[/{pnl_color}]",
        )
    console.print(monthly_table)

    # By symbol
    sym_table = Table(title="Performance by Symbol")
    sym_table.add_column("Symbol", style="bold")
    sym_table.add_column("Trades", justify="right")
    sym_table.add_column("Win Rate", justify="right")
    sym_table.add_column("P&L", justify="right")
    for sym in sorted(m["by_symbol"].keys()):
        data = m["by_symbol"][sym]
        wr = data["wins"] / data["trades"] * 100 if data["trades"] > 0 else 0
        pnl_color = "green" if data["pnl"] >= 0 else "red"
        sym_table.add_row(
            sym, str(data["trades"]), f"{wr:.0f}%",
            f"[{pnl_color}]${data['pnl']:,.2f}[/{pnl_color}]",
        )
    console.print(sym_table)

    # By side
    side_table = Table(title="Performance by Side")
    side_table.add_column("Side", style="bold")
    side_table.add_column("Trades", justify="right")
    side_table.add_column("Win Rate", justify="right")
    side_table.add_column("P&L", justify="right")
    for side in sorted(m["by_side"].keys()):
        data = m["by_side"][side]
        wr = data["wins"] / data["trades"] * 100 if data["trades"] > 0 else 0
        pnl_color = "green" if data["pnl"] >= 0 else "red"
        side_table.add_row(
            side, str(data["trades"]), f"{wr:.0f}%",
            f"[{pnl_color}]${data['pnl']:,.2f}[/{pnl_color}]",
        )
    console.print(side_table)

    # By day of week
    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow_table = Table(title="Performance by Day of Week")
    dow_table.add_column("Day", style="bold")
    dow_table.add_column("Trades", justify="right")
    dow_table.add_column("Win Rate", justify="right")
    dow_table.add_column("P&L", justify="right")
    for dow in dow_order:
        if dow in m["by_dow"]:
            data = m["by_dow"][dow]
            wr = data["wins"] / data["trades"] * 100 if data["trades"] > 0 else 0
            pnl_color = "green" if data["pnl"] >= 0 else "red"
            dow_table.add_row(
                dow, str(data["trades"]), f"{wr:.0f}%",
                f"[{pnl_color}]${data['pnl']:,.2f}[/{pnl_color}]",
            )
    console.print(dow_table)


@app.command()
def analyze(
    csv_path: str = typer.Argument(..., help="Path to trade journal CSV file"),
) -> None:
    """Analyze trades from a CSV and display a full performance dashboard."""
    trades = _parse_csv(csv_path)
    metrics = _compute_metrics(trades)
    _print_metrics_dashboard(metrics)


@app.command()
def equity(
    csv_path: str = typer.Argument(..., help="Path to trade journal CSV file"),
) -> None:
    """Print an ASCII equity curve from trade data."""
    trades = _parse_csv(csv_path)
    metrics = _compute_metrics(trades)
    eq = metrics["equity"]

    if not eq:
        console.print("[red]No equity data to plot.[/red]")
        raise typer.Exit(1)

    chart_width = 60
    chart_height = 20
    min_eq = min(eq)
    max_eq = max(eq)
    eq_range = max_eq - min_eq if max_eq != min_eq else 1

    # Resample equity to chart_width points
    if len(eq) > chart_width:
        step = len(eq) / chart_width
        sampled = [eq[int(i * step)] for i in range(chart_width)]
    else:
        sampled = eq

    # Build chart
    lines = []
    for row in range(chart_height, -1, -1):
        threshold = min_eq + (row / chart_height) * eq_range
        line = ""
        for val in sampled:
            if val >= threshold:
                line += "█"
            else:
                line += " "
        label = f"${threshold:>10,.0f} │"
        lines.append(label + line)

    lines.append(" " * 12 + "└" + "─" * len(sampled))

    chart_text = "\n".join(lines)
    console.print(
        Panel(
            chart_text,
            title=f"Equity Curve ({len(eq)} trades)",
            subtitle=f"Final: ${eq[-1]:,.2f}",
            border_style="blue",
        )
    )


@app.command()
def compare(
    csv1: str = typer.Argument(..., help="Path to first CSV"),
    csv2: str = typer.Argument(..., help="Path to second CSV"),
) -> None:
    """Compare metrics from two trade journals side by side."""
    trades1 = _parse_csv(csv1)
    trades2 = _parse_csv(csv2)
    m1 = _compute_metrics(trades1)
    m2 = _compute_metrics(trades2)

    table = Table(title="Trade Journal Comparison")
    table.add_column("Metric", style="bold")
    table.add_column(Path(csv1).name, justify="right")
    table.add_column(Path(csv2).name, justify="right")

    def _pnl_str(val: float) -> str:
        color = "green" if val >= 0 else "red"
        return f"[{color}]${val:,.2f}[/{color}]"

    pf1 = f"{m1['profit_factor']:.2f}" if m1["profit_factor"] != float("inf") else "∞"
    pf2 = f"{m2['profit_factor']:.2f}" if m2["profit_factor"] != float("inf") else "∞"

    rows = [
        ("Total Trades", str(m1["total_trades"]), str(m2["total_trades"])),
        ("Win Rate", f"{m1['win_rate']:.1f}%", f"{m2['win_rate']:.1f}%"),
        ("Profit Factor", pf1, pf2),
        ("Total P&L", _pnl_str(m1["total_pnl"]), _pnl_str(m2["total_pnl"])),
        ("Average Win", _pnl_str(m1["avg_win"]), _pnl_str(m2["avg_win"])),
        ("Average Loss", _pnl_str(m1["avg_loss"]), _pnl_str(m2["avg_loss"])),
        ("Largest Win", _pnl_str(m1["largest_win"]), _pnl_str(m2["largest_win"])),
        ("Largest Loss", _pnl_str(m1["largest_loss"]), _pnl_str(m2["largest_loss"])),
        ("Max Consec Wins", str(m1["max_consec_wins"]), str(m2["max_consec_wins"])),
        ("Max Consec Losses", str(m1["max_consec_losses"]), str(m2["max_consec_losses"])),
        ("Sharpe Ratio", f"{m1['sharpe']:.2f}", f"{m2['sharpe']:.2f}"),
        ("Max Drawdown", _pnl_str(-m1["max_drawdown"]), _pnl_str(-m2["max_drawdown"])),
        ("Avg Trade Spacing", f"{m1['avg_duration_days']:.1f}d", f"{m2['avg_duration_days']:.1f}d"),
    ]
    for label, v1, v2 in rows:
        table.add_row(label, v1, v2)

    console.print(table)


@app.command()
def export(
    csv_path: str = typer.Argument(..., help="Path to trade journal CSV file"),
    output: str = typer.Option(None, "--output", "-o", help="Output file path (default: stdout)"),
) -> None:
    """Export trade analysis as a formatted markdown report."""
    trades = _parse_csv(csv_path)
    m = _compute_metrics(trades)

    pf_str = f"{m['profit_factor']:.2f}" if m["profit_factor"] != float("inf") else "∞"

    lines = [
        "# Trade Journal Report",
        "",
        f"**Source:** {csv_path}",
        f"**Period:** {trades[0]['date'].strftime('%Y-%m-%d')} to {trades[-1]['date'].strftime('%Y-%m-%d')}",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Trades | {m['total_trades']} |",
        f"| Win Rate | {m['win_rate']:.1f}% |",
        f"| Profit Factor | {pf_str} |",
        f"| Total P&L | ${m['total_pnl']:,.2f} |",
        f"| Average Win | ${m['avg_win']:,.2f} |",
        f"| Average Loss | ${m['avg_loss']:,.2f} |",
        f"| Largest Win | ${m['largest_win']:,.2f} |",
        f"| Largest Loss | ${m['largest_loss']:,.2f} |",
        f"| Max Consecutive Wins | {m['max_consec_wins']} |",
        f"| Max Consecutive Losses | {m['max_consec_losses']} |",
        f"| Sharpe Ratio | {m['sharpe']:.2f} |",
        f"| Max Drawdown | ${m['max_drawdown']:,.2f} ({m['dd_peak_date'].strftime('%Y-%m-%d')} to {m['dd_trough_date'].strftime('%Y-%m-%d')}) |",
        f"| Avg Trade Spacing | {m['avg_duration_days']:.1f} days |",
        "",
        "## Monthly Breakdown",
        "",
        "| Month | Trades | Win Rate | P&L |",
        "|-------|--------|----------|-----|",
    ]
    for month in sorted(m["monthly"].keys()):
        data = m["monthly"][month]
        wr = data["wins"] / data["trades"] * 100 if data["trades"] > 0 else 0
        lines.append(f"| {month} | {data['trades']} | {wr:.0f}% | ${data['pnl']:,.2f} |")

    lines.extend([
        "",
        "## Performance by Symbol",
        "",
        "| Symbol | Trades | Win Rate | P&L |",
        "|--------|--------|----------|-----|",
    ])
    for sym in sorted(m["by_symbol"].keys()):
        data = m["by_symbol"][sym]
        wr = data["wins"] / data["trades"] * 100 if data["trades"] > 0 else 0
        lines.append(f"| {sym} | {data['trades']} | {wr:.0f}% | ${data['pnl']:,.2f} |")

    lines.extend([
        "",
        "## Performance by Side",
        "",
        "| Side | Trades | Win Rate | P&L |",
        "|------|--------|----------|-----|",
    ])
    for side in sorted(m["by_side"].keys()):
        data = m["by_side"][side]
        wr = data["wins"] / data["trades"] * 100 if data["trades"] > 0 else 0
        lines.append(f"| {side} | {data['trades']} | {wr:.0f}% | ${data['pnl']:,.2f} |")

    report = "\n".join(lines) + "\n"

    if output:
        Path(output).write_text(report)
        console.print(f"[green]Report exported to {output}[/green]")
    else:
        console.print(report)


if __name__ == "__main__":
    app()
