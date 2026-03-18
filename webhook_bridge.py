"""Webhook Bridge — Receive TradingView alerts via HTTP and log them."""

import csv
import io
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

app = typer.Typer(
    name="webhook-bridge",
    help="Receive TradingView webhook alerts and log them to SQLite.",
    add_completion=False,
)
console = Console()

DB_PATH = Path("trades.db")

REQUIRED_FIELDS = {"symbol", "side", "price", "strategy_name", "message"}


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


def _init_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Initialise the SQLite database and return a connection."""
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS signals (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT    NOT NULL,
            symbol      TEXT    NOT NULL,
            side        TEXT    NOT NULL,
            price       REAL    NOT NULL,
            strategy_name TEXT  NOT NULL,
            message     TEXT    NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def _insert_signal(
    conn: sqlite3.Connection,
    symbol: str,
    side: str,
    price: float,
    strategy_name: str,
    message: str,
    timestamp: Optional[str] = None,
) -> int:
    """Insert a signal row and return its id."""
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        "INSERT INTO signals (timestamp, symbol, side, price, strategy_name, message) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (ts, symbol, side, price, strategy_name, message),
    )
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def _fetch_signals(
    db_path: Path = DB_PATH,
    limit: Optional[int] = None,
) -> list[dict]:
    """Return signals ordered by timestamp descending."""
    if not db_path.exists():
        return []
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    query = "SELECT * FROM signals ORDER BY timestamp DESC"
    if limit:
        query += f" LIMIT {limit}"
    rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Rich console helpers
# ---------------------------------------------------------------------------


def _print_signal(signal: dict) -> None:
    """Print a Rich-formatted alert panel for a signal."""
    side_color = "green" if signal["side"].upper() == "BUY" else "red"
    header = Text()
    header.append(f" {signal['side'].upper()} ", style=f"bold white on {side_color}")
    header.append(f"  {signal['symbol']}", style="bold cyan")
    header.append(f"  @ {signal['price']}", style="bold yellow")

    body = (
        f"Strategy: [bold]{signal['strategy_name']}[/bold]\n"
        f"Message:  {signal['message']}\n"
        f"Time:     {signal['timestamp']}"
    )
    console.print(Panel(body, title=header, border_style=side_color))


def _signals_table(signals: list[dict]) -> Table:
    """Build a Rich Table from a list of signal dicts."""
    table = Table(title="Webhook Signal History", show_lines=True)
    table.add_column("#", style="dim", justify="right")
    table.add_column("Timestamp", style="cyan")
    table.add_column("Symbol", style="bold")
    table.add_column("Side", justify="center")
    table.add_column("Price", justify="right", style="yellow")
    table.add_column("Strategy", style="magenta")
    table.add_column("Message")

    for s in signals:
        side_style = "green" if s["side"].upper() == "BUY" else "red"
        table.add_row(
            str(s["id"]),
            s["timestamp"],
            s["symbol"],
            Text(s["side"].upper(), style=f"bold {side_style}"),
            f"{s['price']:.2f}",
            s["strategy_name"],
            s["message"],
        )
    return table


# ---------------------------------------------------------------------------
# Telegram forwarding
# ---------------------------------------------------------------------------


def _send_telegram(
    token: str,
    chat_id: str,
    signal: dict,
) -> bool:
    """Forward a signal to Telegram. Returns True on success."""
    try:
        import urllib.request
        import json

        arrow = "\u2B06" if signal["side"].upper() == "BUY" else "\u2B07"
        text = (
            f"{arrow} *{signal['side'].upper()}* {signal['symbol']} "
            f"@ {signal['price']}\n"
            f"Strategy: {signal['strategy_name']}\n"
            f"{signal['message']}"
        )
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps(
            {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        ).encode()
        req = urllib.request.Request(
            url, data=payload, headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as exc:
        console.print(f"[yellow]Telegram send failed: {exc}[/yellow]")
        return False


# ---------------------------------------------------------------------------
# FastAPI app factory
# ---------------------------------------------------------------------------


def create_app(
    db_path: Path = DB_PATH,
    telegram_token: Optional[str] = None,
    telegram_chat_id: Optional[str] = None,
) -> "FastAPI":
    """Build and return the FastAPI application."""
    from fastapi import FastAPI
    from pydantic import BaseModel, field_validator

    class WebhookPayload(BaseModel):
        symbol: str
        side: str
        price: float
        strategy_name: str
        message: str

        @field_validator("side")
        @classmethod
        def validate_side(cls, v: str) -> str:
            if v.lower() not in ("buy", "sell"):
                raise ValueError("side must be 'buy' or 'sell'")
            return v.lower()

        @field_validator("price")
        @classmethod
        def validate_price(cls, v: float) -> float:
            if v <= 0:
                raise ValueError("price must be positive")
            return v

    api = FastAPI(title="Webhook Bridge", version="0.1.0")
    conn = _init_db(db_path)

    @api.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @api.post("/webhook")
    def receive_webhook(payload: WebhookPayload) -> dict:  # noqa: B008
        ts = datetime.now(timezone.utc).isoformat()
        signal = {
            "timestamp": ts,
            "symbol": payload.symbol,
            "side": payload.side,
            "price": payload.price,
            "strategy_name": payload.strategy_name,
            "message": payload.message,
        }
        row_id = _insert_signal(
            conn,
            payload.symbol,
            payload.side,
            payload.price,
            payload.strategy_name,
            payload.message,
            timestamp=ts,
        )
        signal["id"] = row_id
        _print_signal(signal)

        if telegram_token and telegram_chat_id:
            _send_telegram(telegram_token, telegram_chat_id, signal)

        return {"status": "received", "id": row_id}

    return api


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------


@app.command()
def serve(
    port: int = typer.Option(8080, "--port", "-p", help="Port to listen on."),
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind to."),
    db: str = typer.Option("trades.db", "--db", help="SQLite database path."),
    telegram_token: Optional[str] = typer.Option(
        None, "--telegram-token", help="Telegram bot token for forwarding."
    ),
    telegram_chat_id: Optional[str] = typer.Option(
        None, "--telegram-chat-id", help="Telegram chat ID for forwarding."
    ),
) -> None:
    """Start the webhook bridge server."""
    import uvicorn

    db_path = Path(db)
    api = create_app(
        db_path=db_path,
        telegram_token=telegram_token,
        telegram_chat_id=telegram_chat_id,
    )
    console.print(
        Panel(
            f"[bold green]Webhook Bridge listening on {host}:{port}[/bold green]\n"
            f"Database: {db_path.resolve()}\n"
            f"Telegram: {'enabled' if telegram_token else 'disabled'}\n\n"
            f"POST http://{host}:{port}/webhook",
            title="[bold]Webhook Bridge[/bold]",
        )
    )
    uvicorn.run(api, host=host, port=port, log_level="info")


@app.command()
def history(
    n: int = typer.Option(20, "--last", "-n", help="Number of signals to show."),
    db: str = typer.Option("trades.db", "--db", help="SQLite database path."),
) -> None:
    """Show last N webhook signals as a Rich table."""
    db_path = Path(db)
    if not db_path.exists():
        console.print("[red]No database found. Run 'serve' first to create one.[/red]")
        raise typer.Exit(1)

    signals = _fetch_signals(db_path, limit=n)
    if not signals:
        console.print("[yellow]No signals recorded yet.[/yellow]")
        raise typer.Exit(0)

    console.print(_signals_table(signals))


@app.command()
def export(
    db: str = typer.Option("trades.db", "--db", help="SQLite database path."),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output CSV file (default: stdout)."
    ),
) -> None:
    """Export signals to CSV in trade_journal.py format.

    Output columns: date,symbol,side,entry_price,exit_price,quantity,pnl,fees
    Signals are exported as open entries (exit_price, pnl, fees set to 0).
    Pipe to trade_journal.py analyze for full performance stats.
    """
    db_path = Path(db)
    if not db_path.exists():
        console.print("[red]No database found.[/red]", highlight=False)
        raise typer.Exit(1)

    signals = _fetch_signals(db_path)
    if not signals:
        console.print("[yellow]No signals to export.[/yellow]")
        raise typer.Exit(0)

    # Reverse so oldest-first (fetch returns newest-first)
    signals.reverse()

    buf = io.StringIO() if output is None else None
    dest = open(output, "w", newline="") if output else buf  # noqa: SIM115
    assert dest is not None

    writer = csv.writer(dest)
    writer.writerow(
        ["date", "symbol", "side", "entry_price", "exit_price", "quantity", "pnl", "fees"]
    )
    for s in signals:
        # Parse ISO timestamp to date string
        dt = s["timestamp"][:10]
        side = "LONG" if s["side"].lower() == "buy" else "SHORT"
        writer.writerow([dt, s["symbol"], side, f"{s['price']:.2f}", "0.00", "0", "0.00", "0.00"])

    if output:
        dest.close()
        console.print(f"[green]Exported {len(signals)} signals to {output}[/green]")
    else:
        assert buf is not None
        sys.stdout.write(buf.getvalue())


@app.command()
def stats(
    db: str = typer.Option("trades.db", "--db", help="SQLite database path."),
) -> None:
    """Quick summary stats from the signal database."""
    db_path = Path(db)
    if not db_path.exists():
        console.print("[red]No database found.[/red]", highlight=False)
        raise typer.Exit(1)

    conn = sqlite3.connect(str(db_path))

    total = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
    if total == 0:
        console.print("[yellow]No signals recorded yet.[/yellow]")
        conn.close()
        raise typer.Exit(0)

    # Signals per strategy
    strat_rows = conn.execute(
        "SELECT strategy_name, COUNT(*) as cnt FROM signals "
        "GROUP BY strategy_name ORDER BY cnt DESC"
    ).fetchall()

    # Signals per symbol
    sym_rows = conn.execute(
        "SELECT symbol, COUNT(*) as cnt FROM signals "
        "GROUP BY symbol ORDER BY cnt DESC"
    ).fetchall()

    # Signals per day
    day_rows = conn.execute(
        "SELECT SUBSTR(timestamp, 1, 10) as day, COUNT(*) as cnt FROM signals "
        "GROUP BY day ORDER BY day DESC LIMIT 14"
    ).fetchall()

    # Last signal
    last = conn.execute(
        "SELECT timestamp FROM signals ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    conn.close()

    # Strategy table
    t1 = Table(title="Signals per Strategy")
    t1.add_column("Strategy", style="magenta")
    t1.add_column("Count", justify="right", style="bold")
    for name, cnt in strat_rows:
        t1.add_row(name, str(cnt))

    # Symbol table
    t2 = Table(title="Signals per Symbol")
    t2.add_column("Symbol", style="cyan")
    t2.add_column("Count", justify="right", style="bold")
    for sym, cnt in sym_rows:
        t2.add_row(sym, str(cnt))

    # Daily table
    t3 = Table(title="Signals per Day (last 14 days)")
    t3.add_column("Date", style="cyan")
    t3.add_column("Count", justify="right", style="bold")
    for day, cnt in day_rows:
        t3.add_row(day, str(cnt))

    console.print(Panel(f"[bold]Total signals:[/bold] {total}", title="Summary"))
    console.print(t1)
    console.print(t2)
    console.print(t3)
    console.print(f"\n[dim]Last signal:[/dim] {last[0]}")


if __name__ == "__main__":
    app()
