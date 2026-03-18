#!/usr/bin/env python3
"""Funding Rate Scanner — Typer+Rich CLI for crypto funding rate analysis via CCXT."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Optional

import ccxt
import typer
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.text import Text

app = typer.Typer(
    name="funding-scanner",
    help="Crypto perpetual funding rate scanner and arbitrage detector.",
    no_args_is_help=True,
)
console = Console()

SUPPORTED_EXCHANGES = {"bybit", "binance", "okx"}


def _get_exchange(name: str) -> ccxt.Exchange:
    """Create a CCXT exchange instance (no API keys needed for public data)."""
    name = name.lower()
    if name not in SUPPORTED_EXCHANGES:
        console.print(f"[red]Unsupported exchange: {name}[/red]")
        raise typer.Exit(1)
    exchange_class = getattr(ccxt, name)
    exchange = exchange_class({"enableRateLimit": True})
    return exchange


def _fetch_funding_rates(exchange: ccxt.Exchange) -> list[dict]:
    """Fetch funding rates for all USDT perpetual pairs."""
    rates = exchange.fetch_funding_rates()
    results = []
    for symbol, data in rates.items():
        if "USDT" not in symbol or ":USDT" not in symbol:
            continue
        rate = data.get("fundingRate")
        if rate is None:
            continue
        annualized = rate * 3 * 365
        next_ts = data.get("fundingTimestamp") or data.get("nextFundingTimestamp")
        next_time = ""
        if next_ts:
            next_time = datetime.fromtimestamp(
                next_ts / 1000, tz=timezone.utc
            ).strftime("%Y-%m-%d %H:%M UTC")
        info = data.get("info", {})
        volume_24h = None
        for key in ("turnover24h", "volume24h", "volCcy24h", "quoteVolume"):
            if key in info and info[key]:
                try:
                    volume_24h = float(info[key])
                    break
                except (ValueError, TypeError):
                    pass
        results.append(
            {
                "symbol": data.get("symbol", symbol),
                "rate": rate,
                "annualized": annualized,
                "annualized_pct": annualized * 100,
                "next_funding_time": next_time,
                "volume_24h": volume_24h,
            }
        )
    results.sort(key=lambda x: abs(x["annualized"]), reverse=True)
    return results


def _build_scan_table(
    rates: list[dict], exchange_name: str, top: int | None = None
) -> Table:
    """Build a Rich table from funding rate data."""
    table = Table(
        title=f"Funding Rates — {exchange_name.upper()}",
        caption="Sorted by absolute annualized rate",
    )
    table.add_column("Symbol", style="bold")
    table.add_column("Current Rate", justify="right")
    table.add_column("Annualized %", justify="right")
    table.add_column("Next Funding", justify="center")
    table.add_column("24h Volume", justify="right")

    display = rates[:top] if top else rates
    for r in display:
        ann_pct = r["annualized_pct"]
        if ann_pct > 25:
            color = "green"
        elif ann_pct < -25:
            color = "red"
        elif ann_pct > 0:
            color = "bright_green"
        else:
            color = "bright_red"

        rate_str = f"{r['rate']:.6f}"
        ann_str = f"[{color}]{ann_pct:+.2f}%[/{color}]"
        vol_str = (
            f"${r['volume_24h']:,.0f}" if r["volume_24h"] is not None else "N/A"
        )
        table.add_row(
            r["symbol"], rate_str, ann_str, r["next_funding_time"], vol_str
        )
    return table


@app.command()
def scan(
    exchange: str = typer.Option("bybit", "--exchange", "-e", help="Exchange to scan"),
    top: Optional[int] = typer.Option(None, "--top", "-t", help="Show only top N pairs"),
    watch: bool = typer.Option(False, "--watch", "-w", help="Auto-refresh every 60s"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
) -> None:
    """Scan current funding rates for all USDT perpetual pairs."""
    ex = _get_exchange(exchange)

    def _do_scan() -> list[dict]:
        with console.status(f"[bold]Fetching funding rates from {exchange}..."):
            return _fetch_funding_rates(ex)

    if watch and not json_output:
        try:
            while True:
                rates = _do_scan()
                os.system("clear" if os.name != "nt" else "cls")
                table = _build_scan_table(rates, exchange, top)
                console.print(table)
                console.print(
                    f"\n[dim]Last updated: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')} — refreshing in 60s (Ctrl+C to stop)[/dim]"
                )
                time.sleep(60)
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopped.[/yellow]")
            return
    else:
        rates = _do_scan()
        if json_output:
            display = rates[:top] if top else rates
            print(json.dumps(display, indent=2, default=str))
        else:
            table = _build_scan_table(rates, exchange, top)
            console.print(table)
            flagged = [r for r in rates if abs(r["annualized_pct"]) > 25]
            if flagged:
                console.print(
                    f"\n[bold yellow]⚠ {len(flagged)} pairs with annualized rate above ±25%[/bold yellow]"
                )


@app.command()
def history(
    symbol: str = typer.Argument(..., help="Trading pair symbol (e.g. BTC/USDT:USDT)"),
    exchange: str = typer.Option("bybit", "--exchange", "-e", help="Exchange"),
) -> None:
    """Show last 30 funding rate data points for a symbol."""
    ex = _get_exchange(exchange)
    with console.status(f"[bold]Fetching funding history for {symbol}..."):
        try:
            history_data = ex.fetch_funding_rate_history(symbol, limit=30)
        except Exception as e:
            console.print(f"[red]Error fetching history: {e}[/red]")
            raise typer.Exit(1)

    if not history_data:
        console.print(f"[yellow]No funding history found for {symbol}[/yellow]")
        raise typer.Exit(1)

    rates = [entry.get("fundingRate", 0) for entry in history_data]
    timestamps = []
    for entry in history_data:
        ts = entry.get("timestamp")
        if ts:
            timestamps.append(
                datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime(
                    "%m-%d %H:%M"
                )
            )
        else:
            timestamps.append("N/A")

    table = Table(title=f"Funding Rate History — {symbol} ({exchange.upper()})")
    table.add_column("Time", style="dim")
    table.add_column("Rate", justify="right")
    table.add_column("Annualized %", justify="right")
    table.add_column("Bar", justify="left")

    max_abs = max(abs(r) for r in rates) if rates else 1
    bar_width = 30

    for ts, rate in zip(timestamps, rates):
        ann = rate * 3 * 365 * 100
        if ann > 0:
            color = "green"
        else:
            color = "red"
        bar_len = int(abs(rate) / max_abs * bar_width) if max_abs > 0 else 0
        bar_char = "█" * bar_len
        bar_str = f"[{color}]{bar_char}[/{color}]"
        table.add_row(ts, f"{rate:.6f}", f"[{color}]{ann:+.2f}%[/{color}]", bar_str)

    console.print(table)

    avg_rate = sum(rates) / len(rates)
    avg_ann = avg_rate * 3 * 365 * 100
    console.print(f"\n[bold]Average rate:[/bold] {avg_rate:.6f} ({avg_ann:+.2f}% annualized)")
    console.print(f"[bold]Min:[/bold] {min(rates):.6f}  [bold]Max:[/bold] {max(rates):.6f}")


@app.command()
def arbitrage(
    top: Optional[int] = typer.Option(None, "--top", "-t", help="Show only top N opportunities"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
) -> None:
    """Compare funding rates across Bybit, Binance, and OKX for arbitrage opportunities."""
    exchanges = {}
    all_rates: dict[str, dict[str, dict]] = {}

    for name in ["bybit", "binance", "okx"]:
        try:
            with console.status(f"[bold]Fetching rates from {name}..."):
                ex = _get_exchange(name)
                rates = _fetch_funding_rates(ex)
                exchanges[name] = {r["symbol"]: r for r in rates}
                for r in rates:
                    base = r["symbol"].split("/")[0] if "/" in r["symbol"] else r["symbol"]
                    if base not in all_rates:
                        all_rates[base] = {}
                    all_rates[base][name] = r
        except Exception as e:
            console.print(f"[yellow]Warning: Could not fetch from {name}: {e}[/yellow]")

    opportunities = []
    for base, ex_data in all_rates.items():
        if len(ex_data) < 2:
            continue
        names = list(ex_data.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                e1, e2 = names[i], names[j]
                r1 = ex_data[e1]["annualized_pct"]
                r2 = ex_data[e2]["annualized_pct"]
                spread = abs(r1 - r2)
                if spread > 10:
                    long_ex = e1 if r1 < r2 else e2
                    short_ex = e2 if r1 < r2 else e1
                    long_rate = min(r1, r2)
                    short_rate = max(r1, r2)
                    opportunities.append(
                        {
                            "symbol": base,
                            "long_exchange": long_ex,
                            "short_exchange": short_ex,
                            "long_rate_pct": long_rate,
                            "short_rate_pct": short_rate,
                            "spread_pct": spread,
                            "direction": f"Long {long_ex} / Short {short_ex}",
                        }
                    )

    opportunities.sort(key=lambda x: x["spread_pct"], reverse=True)
    if top:
        opportunities = opportunities[:top]

    if json_output:
        print(json.dumps(opportunities, indent=2, default=str))
        return

    table = Table(
        title="Funding Rate Arbitrage Opportunities (>10% annualized spread)",
        caption=f"Scanned: {', '.join(SUPPORTED_EXCHANGES)}",
    )
    table.add_column("Symbol", style="bold")
    table.add_column("Long Exchange", style="green")
    table.add_column("Long Rate %", justify="right")
    table.add_column("Short Exchange", style="red")
    table.add_column("Short Rate %", justify="right")
    table.add_column("Spread %", justify="right", style="bold yellow")

    for opp in opportunities:
        table.add_row(
            opp["symbol"],
            opp["long_exchange"],
            f"{opp['long_rate_pct']:+.2f}%",
            opp["short_exchange"],
            f"{opp['short_rate_pct']:+.2f}%",
            f"{opp['spread_pct']:.2f}%",
        )

    console.print(table)
    if not opportunities:
        console.print(
            "[dim]No arbitrage opportunities found with >10% annualized spread.[/dim]"
        )
    else:
        console.print(
            f"\n[bold]{len(opportunities)} arbitrage opportunities found.[/bold]"
        )


if __name__ == "__main__":
    app()
