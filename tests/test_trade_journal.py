"""Tests for the trade_journal.py CLI tool."""

import csv
import math
import tempfile
from datetime import datetime
from pathlib import Path

import click
import pytest
import typer
from typer.testing import CliRunner

from trade_journal import _compute_metrics, _parse_csv, app

runner = CliRunner()

SAMPLE_CSV = Path(__file__).parent.parent / "sample_trades.csv"


def _make_csv(rows: list[dict], tmp_path: Path) -> Path:
    """Write a temporary CSV with trade data."""
    p = tmp_path / "trades.csv"
    fieldnames = ["date", "symbol", "side", "entry_price", "exit_price", "quantity", "pnl", "fees"]
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)
    return p


def _basic_trades() -> list[dict]:
    """Return a small set of test trades."""
    return [
        {"date": "2025-01-01", "symbol": "BTC", "side": "LONG", "entry_price": "40000", "exit_price": "41000", "quantity": "0.1", "pnl": "100", "fees": "2"},
        {"date": "2025-01-02", "symbol": "ETH", "side": "SHORT", "entry_price": "2500", "exit_price": "2450", "quantity": "1", "pnl": "50", "fees": "1"},
        {"date": "2025-01-03", "symbol": "BTC", "side": "LONG", "entry_price": "41000", "exit_price": "40500", "quantity": "0.1", "pnl": "-50", "fees": "2"},
        {"date": "2025-01-04", "symbol": "SOL", "side": "LONG", "entry_price": "100", "exit_price": "110", "quantity": "5", "pnl": "50", "fees": "0.5"},
        {"date": "2025-01-05", "symbol": "BTC", "side": "SHORT", "entry_price": "40800", "exit_price": "41200", "quantity": "0.1", "pnl": "-40", "fees": "2"},
    ]


class TestParseCSV:
    def test_parse_valid_csv(self, tmp_path: Path) -> None:
        csv_path = _make_csv(_basic_trades(), tmp_path)
        trades = _parse_csv(str(csv_path))
        assert len(trades) == 5
        assert trades[0]["symbol"] == "BTC"
        assert trades[0]["pnl"] == 100.0

    def test_parse_missing_file(self) -> None:
        with pytest.raises(click.exceptions.Exit):
            _parse_csv("/nonexistent/file.csv")

    def test_parse_empty_csv(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.csv"
        p.write_text("date,symbol,side,entry_price,exit_price,quantity,pnl,fees\n")
        with pytest.raises(click.exceptions.Exit):
            _parse_csv(str(p))

    def test_trades_sorted_by_date(self, tmp_path: Path) -> None:
        trades_data = _basic_trades()
        trades_data[0]["date"] = "2025-01-10"  # Move first trade to later date
        csv_path = _make_csv(trades_data, tmp_path)
        trades = _parse_csv(str(csv_path))
        dates = [t["date"] for t in trades]
        assert dates == sorted(dates)


class TestComputeMetrics:
    def test_total_trades(self, tmp_path: Path) -> None:
        csv_path = _make_csv(_basic_trades(), tmp_path)
        trades = _parse_csv(str(csv_path))
        m = _compute_metrics(trades)
        assert m["total_trades"] == 5

    def test_win_rate(self, tmp_path: Path) -> None:
        csv_path = _make_csv(_basic_trades(), tmp_path)
        trades = _parse_csv(str(csv_path))
        m = _compute_metrics(trades)
        # 3 wins (net pnl > 0): trade 1 (98), trade 2 (49), trade 4 (49.5)
        # 2 losses: trade 3 (-52), trade 5 (-42)
        assert m["win_rate"] == 60.0

    def test_profit_factor(self, tmp_path: Path) -> None:
        csv_path = _make_csv(_basic_trades(), tmp_path)
        trades = _parse_csv(str(csv_path))
        m = _compute_metrics(trades)
        assert m["profit_factor"] > 0

    def test_total_pnl(self, tmp_path: Path) -> None:
        csv_path = _make_csv(_basic_trades(), tmp_path)
        trades = _parse_csv(str(csv_path))
        m = _compute_metrics(trades)
        # Sum of (pnl - fees) for all trades
        expected = (100 - 2) + (50 - 1) + (-50 - 2) + (50 - 0.5) + (-40 - 2)
        assert abs(m["total_pnl"] - expected) < 0.01

    def test_max_consecutive_wins(self, tmp_path: Path) -> None:
        csv_path = _make_csv(_basic_trades(), tmp_path)
        trades = _parse_csv(str(csv_path))
        m = _compute_metrics(trades)
        assert m["max_consec_wins"] >= 1

    def test_max_drawdown_non_negative(self, tmp_path: Path) -> None:
        csv_path = _make_csv(_basic_trades(), tmp_path)
        trades = _parse_csv(str(csv_path))
        m = _compute_metrics(trades)
        assert m["max_drawdown"] >= 0

    def test_sharpe_ratio_finite(self, tmp_path: Path) -> None:
        csv_path = _make_csv(_basic_trades(), tmp_path)
        trades = _parse_csv(str(csv_path))
        m = _compute_metrics(trades)
        assert math.isfinite(m["sharpe"])

    def test_by_symbol_breakdown(self, tmp_path: Path) -> None:
        csv_path = _make_csv(_basic_trades(), tmp_path)
        trades = _parse_csv(str(csv_path))
        m = _compute_metrics(trades)
        assert "BTC" in m["by_symbol"]
        assert "ETH" in m["by_symbol"]
        assert "SOL" in m["by_symbol"]
        assert m["by_symbol"]["BTC"]["trades"] == 3

    def test_by_side_breakdown(self, tmp_path: Path) -> None:
        csv_path = _make_csv(_basic_trades(), tmp_path)
        trades = _parse_csv(str(csv_path))
        m = _compute_metrics(trades)
        assert "LONG" in m["by_side"]
        assert "SHORT" in m["by_side"]
        assert m["by_side"]["LONG"]["trades"] == 3
        assert m["by_side"]["SHORT"]["trades"] == 2

    def test_monthly_breakdown(self, tmp_path: Path) -> None:
        csv_path = _make_csv(_basic_trades(), tmp_path)
        trades = _parse_csv(str(csv_path))
        m = _compute_metrics(trades)
        assert "2025-01" in m["monthly"]
        assert m["monthly"]["2025-01"]["trades"] == 5


class TestCLICommands:
    def test_analyze_command(self) -> None:
        result = runner.invoke(app, ["analyze", str(SAMPLE_CSV)])
        assert result.exit_code == 0
        assert "Trade Performance Summary" in result.output

    def test_equity_command(self) -> None:
        result = runner.invoke(app, ["equity", str(SAMPLE_CSV)])
        assert result.exit_code == 0
        assert "Equity Curve" in result.output

    def test_compare_command(self) -> None:
        result = runner.invoke(app, ["compare", str(SAMPLE_CSV), str(SAMPLE_CSV)])
        assert result.exit_code == 0
        assert "Trade Journal Comparison" in result.output

    def test_export_command(self, tmp_path: Path) -> None:
        out = tmp_path / "report.md"
        result = runner.invoke(app, ["export", str(SAMPLE_CSV), "--output", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        content = out.read_text()
        assert "# Trade Journal Report" in content
        assert "Win Rate" in content
