#!/usr/bin/env python3
"""Unified Rich Dashboard — All crypto trading tools in one live view."""

from __future__ import annotations

import shutil
import sqlite3
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

app = typer.Typer(
    name="pinescript-dashboard",
    help="Unified Rich dashboard for all crypto trading tools.",
    no_args_is_help=False,
)
console = Console()

DB_PATH = Path("trades.db")


# ---------------------------------------------------------------------------
# Panel builders
# ---------------------------------------------------------------------------


def _build_funding_panel() -> Panel:
    """TOP LEFT: Top 10 extreme funding rates from Bybit."""
    try:
        import ccxt

        exchange = ccxt.bybit({"enableRateLimit": True})
        rates = exchange.fetch_funding_rates()
        results = []
        for symbol, data in rates.items():
            if "USDT" not in symbol or ":USDT" not in symbol:
                continue
            rate = data.get("fundingRate")
            if rate is None:
                continue
            annualized = rate * 3 * 365 * 100
            results.append(
                {
                    "symbol": data.get("symbol", symbol),
                    "rate": rate,
                    "annualized_pct": annualized,
                }
            )
        results.sort(key=lambda x: abs(x["annualized_pct"]), reverse=True)

        table = Table(
            show_header=True,
            header_style="bold cyan",
            expand=True,
            padding=(0, 1),
        )
        table.add_column("Symbol", style="bold white", no_wrap=True)
        table.add_column("Rate", justify="right")
        table.add_column("Annual %", justify="right")

        for r in results[:10]:
            ann = r["annualized_pct"]
            if ann > 25:
                color = "bold green"
            elif ann > 0:
                color = "green"
            elif ann > -25:
                color = "red"
            else:
                color = "bold red"
            table.add_row(
                r["symbol"].replace("/USDT:USDT", ""),
                f"{r['rate']:.6f}",
                f"[{color}]{ann:+.1f}%[/{color}]",
            )

        return Panel(
            table,
            title="[bold bright_yellow]Funding Rates[/bold bright_yellow]",
            subtitle="[dim]Bybit top 10 by |rate|[/dim]",
            border_style="bright_yellow",
        )
    except Exception as e:
        return Panel(
            f"[red]Error fetching funding rates:[/red]\n{e}",
            title="[bold bright_yellow]Funding Rates[/bold bright_yellow]",
            border_style="bright_yellow",
        )


def _build_signals_panel(db_path: Path) -> Panel:
    """TOP RIGHT: Last 10 webhook signals from trades.db."""
    if not db_path.exists():
        return Panel(
            "[dim]No trades.db found.\nRun webhook-bridge serve to start collecting signals.[/dim]",
            title="[bold bright_cyan]Recent Signals[/bold bright_cyan]",
            border_style="bright_cyan",
        )

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM signals ORDER BY timestamp DESC LIMIT 10"
        ).fetchall()
        conn.close()
    except Exception as e:
        return Panel(
            f"[red]DB error:[/red] {e}",
            title="[bold bright_cyan]Recent Signals[/bold bright_cyan]",
            border_style="bright_cyan",
        )

    if not rows:
        return Panel(
            "[dim]No signals recorded yet.[/dim]",
            title="[bold bright_cyan]Recent Signals[/bold bright_cyan]",
            border_style="bright_cyan",
        )

    table = Table(
        show_header=True,
        header_style="bold cyan",
        expand=True,
        padding=(0, 1),
    )
    table.add_column("Time", style="dim", no_wrap=True)
    table.add_column("Symbol", style="bold white", no_wrap=True)
    table.add_column("Side", justify="center")
    table.add_column("Strategy", style="magenta", no_wrap=True)
    table.add_column("Price", justify="right", style="yellow")

    for row in rows:
        r = dict(row)
        ts = r["timestamp"][:16].replace("T", " ")  # trim to minutes
        side = r["side"].upper()
        side_color = "bold green" if side == "BUY" else "bold red"
        table.add_row(
            ts,
            r["symbol"],
            f"[{side_color}]{side}[/{side_color}]",
            r["strategy_name"],
            f"{r['price']:,.2f}",
        )

    return Panel(
        table,
        title="[bold bright_cyan]Recent Signals[/bold bright_cyan]",
        subtitle=f"[dim]Last {len(rows)} from trades.db[/dim]",
        border_style="bright_cyan",
    )


def _build_portfolio_panel(db_path: Path) -> Panel:
    """BOTTOM LEFT: Quick portfolio stats from trades.db."""
    title = "[bold bright_green]Portfolio Stats[/bold bright_green]"
    border = "bright_green"

    if not db_path.exists():
        return Panel(
            "[dim]No trades.db found.\nStats will appear once signals are recorded.[/dim]",
            title=title,
            border_style=border,
        )

    try:
        conn = sqlite3.connect(str(db_path))
        total = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
        if total == 0:
            conn.close()
            return Panel("[dim]No signals recorded yet.[/dim]", title=title, border_style=border)

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        today_count = conn.execute(
            "SELECT COUNT(*) FROM signals WHERE timestamp LIKE ?", (f"{today}%",)
        ).fetchone()[0]

        top_strat = conn.execute(
            "SELECT strategy_name, COUNT(*) as cnt FROM signals "
            "GROUP BY strategy_name ORDER BY cnt DESC LIMIT 1"
        ).fetchone()

        top_sym = conn.execute(
            "SELECT symbol, COUNT(*) as cnt FROM signals "
            "GROUP BY symbol ORDER BY cnt DESC LIMIT 1"
        ).fetchone()

        buy_count = conn.execute(
            "SELECT COUNT(*) FROM signals WHERE LOWER(side)='buy'"
        ).fetchone()[0]
        sell_count = conn.execute(
            "SELECT COUNT(*) FROM signals WHERE LOWER(side)='sell'"
        ).fetchone()[0]

        conn.close()

        grid = Table.grid(padding=(0, 2), expand=True)
        grid.add_column(style="bold")
        grid.add_column(justify="right", style="bright_white")

        grid.add_row("Total Signals", str(total))
        grid.add_row("Signals Today", f"[bright_yellow]{today_count}[/bright_yellow]")
        grid.add_row(
            "Most Active Strategy",
            f"[magenta]{top_strat[0]}[/magenta] ({top_strat[1]})" if top_strat else "—",
        )
        grid.add_row(
            "Most Active Symbol",
            f"[cyan]{top_sym[0]}[/cyan] ({top_sym[1]})" if top_sym else "—",
        )

        if buy_count + sell_count > 0:
            ratio = buy_count / sell_count if sell_count > 0 else float("inf")
            ratio_str = f"{ratio:.2f}" if ratio != float("inf") else "all longs"
            ratio_color = "green" if ratio >= 1 else "red"
            grid.add_row(
                "Long/Short Ratio",
                f"[{ratio_color}]{ratio_str}[/{ratio_color}]  ({buy_count}L / {sell_count}S)",
            )
        else:
            grid.add_row("Long/Short Ratio", "—")

        return Panel(grid, title=title, border_style=border)

    except Exception as e:
        return Panel(f"[red]DB error:[/red] {e}", title=title, border_style=border)


def _build_status_panel(db_path: Path, webhook_port: int) -> Panel:
    """BOTTOM RIGHT: System status — installed tools, webhook health, etc."""
    title = "[bold bright_magenta]System Status[/bold bright_magenta]"
    border = "bright_magenta"

    grid = Table.grid(padding=(0, 2), expand=True)
    grid.add_column(style="bold")
    grid.add_column(justify="right")

    # Check which tool modules are importable
    tools = {
        "pinescript_ai": "Pine Script AI",
        "funding_scanner": "Funding Scanner",
        "trade_journal": "Trade Journal",
        "webhook_bridge": "Webhook Bridge",
    }
    for module, label in tools.items():
        try:
            __import__(module)
            grid.add_row(label, "[green]installed[/green]")
        except ImportError:
            grid.add_row(label, "[red]not found[/red]")

    # Webhook server health check
    try:
        req = urllib.request.Request(
            f"http://localhost:{webhook_port}/health",
            method="GET",
        )
        resp = urllib.request.urlopen(req, timeout=2)
        if resp.status == 200:
            grid.add_row("Webhook Server", f"[green]running[/green] (:{webhook_port})")
        else:
            grid.add_row("Webhook Server", f"[yellow]unhealthy[/yellow] (:{webhook_port})")
    except Exception:
        grid.add_row("Webhook Server", f"[dim]offline[/dim] (:{webhook_port})")

    # Last signal age
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            last = conn.execute(
                "SELECT timestamp FROM signals ORDER BY timestamp DESC LIMIT 1"
            ).fetchone()
            conn.close()
            if last:
                try:
                    last_dt = datetime.fromisoformat(last[0].replace("Z", "+00:00"))
                    age = datetime.now(timezone.utc) - last_dt
                    secs = int(age.total_seconds())
                    if secs < 60:
                        age_str = f"{secs}s ago"
                    elif secs < 3600:
                        age_str = f"{secs // 60}m ago"
                    elif secs < 86400:
                        age_str = f"{secs // 3600}h ago"
                    else:
                        age_str = f"{secs // 86400}d ago"
                    grid.add_row("Last Signal", age_str)
                except Exception:
                    grid.add_row("Last Signal", last[0][:16])
            else:
                grid.add_row("Last Signal", "[dim]none[/dim]")
        except Exception:
            grid.add_row("Last Signal", "[dim]unknown[/dim]")
    else:
        grid.add_row("Last Signal", "[dim]no database[/dim]")

    # Database size
    if db_path.exists():
        size_bytes = db_path.stat().st_size
        if size_bytes < 1024:
            size_str = f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            size_str = f"{size_bytes / 1024:.1f} KB"
        else:
            size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
        grid.add_row("Database Size", size_str)
    else:
        grid.add_row("Database Size", "[dim]no database[/dim]")

    return Panel(grid, title=title, border_style=border)


# ---------------------------------------------------------------------------
# Layout assembly
# ---------------------------------------------------------------------------


def _build_layout(db_path: Path, webhook_port: int) -> Layout:
    """Build the full 4-panel Rich Layout."""
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
    )
    layout["body"].split_row(
        Layout(name="left"),
        Layout(name="right"),
    )
    layout["left"].split_column(
        Layout(name="top_left"),
        Layout(name="bottom_left"),
    )
    layout["right"].split_column(
        Layout(name="top_right"),
        Layout(name="bottom_right"),
    )

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    header = Table.grid(expand=True)
    header.add_column(justify="center", ratio=1)
    header.add_row(
        f"[bold bright_white on blue]  PINESCRIPT AI — TRADING DASHBOARD  [/bold bright_white on blue]"
        f"    [dim]{now}[/dim]"
    )
    layout["header"].update(header)

    layout["top_left"].update(_build_funding_panel())
    layout["top_right"].update(_build_signals_panel(db_path))
    layout["bottom_left"].update(_build_portfolio_panel(db_path))
    layout["bottom_right"].update(_build_status_panel(db_path, webhook_port))

    return layout


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@app.callback(invoke_without_command=True)
def main(
    no_refresh: bool = typer.Option(
        False, "--no-refresh", help="Single snapshot instead of live refresh."
    ),
    port: int = typer.Option(
        8080, "--port", "-p", help="Webhook server port to check for health."
    ),
    db: str = typer.Option(
        "trades.db", "--db", help="Path to trades.db signal database."
    ),
) -> None:
    """Launch the unified crypto trading dashboard."""
    db_path = Path(db)

    if no_refresh:
        layout = _build_layout(db_path, port)
        console.print(layout)
        return

    console.print("[dim]Starting dashboard (Ctrl+C to quit)...[/dim]\n")
    try:
        with Live(
            _build_layout(db_path, port),
            console=console,
            refresh_per_second=0.5,
            screen=True,
        ) as live:
            import time

            while True:
                live.update(_build_layout(db_path, port))
                time.sleep(30)
    except KeyboardInterrupt:
        console.print("\n[yellow]Dashboard stopped.[/yellow]")


if __name__ == "__main__":
    app()
