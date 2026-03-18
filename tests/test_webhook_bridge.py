"""Tests for webhook_bridge.py — FastAPI webhook receiver + CLI commands."""

from __future__ import annotations

import csv
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from webhook_bridge import (
    _fetch_signals,
    _init_db,
    _insert_signal,
    app,
    create_app,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_db(tmp_path: Path) -> Path:
    """Return a temporary database path."""
    return tmp_path / "test_trades.db"


@pytest.fixture()
def seeded_db(tmp_db: Path) -> Path:
    """Create a database with a few sample signals."""
    conn = _init_db(tmp_db)
    _insert_signal(conn, "BTCUSDT", "buy", 65000.0, "smc_reversal", "CHoCH detected", "2026-03-01T10:00:00+00:00")
    _insert_signal(conn, "ETHUSDT", "sell", 3400.0, "mtf_confluence", "Bearish OB", "2026-03-01T11:00:00+00:00")
    _insert_signal(conn, "BTCUSDT", "sell", 66000.0, "smc_reversal", "Take profit hit", "2026-03-02T09:00:00+00:00")
    _insert_signal(conn, "SOLUSDT", "buy", 145.5, "confluence_scorer", "Score 6/8", "2026-03-02T14:00:00+00:00")
    conn.close()
    return tmp_db


@pytest.fixture()
def client(tmp_db: Path):
    """Return a FastAPI TestClient backed by a temp database."""
    from fastapi.testclient import TestClient

    api = create_app(db_path=tmp_db)
    return TestClient(api)


VALID_PAYLOAD = {
    "symbol": "BTCUSDT",
    "side": "buy",
    "price": 65000.0,
    "strategy_name": "smc_reversal",
    "message": "CHoCH detected on 15m",
}


# ---------------------------------------------------------------------------
# Database unit tests
# ---------------------------------------------------------------------------


class TestDatabase:
    """Test SQLite database helpers."""

    def test_init_creates_table(self, tmp_db: Path) -> None:
        conn = _init_db(tmp_db)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        assert ("signals",) in tables
        conn.close()

    def test_insert_and_fetch(self, tmp_db: Path) -> None:
        conn = _init_db(tmp_db)
        row_id = _insert_signal(conn, "BTCUSDT", "buy", 65000.0, "test_strat", "msg")
        assert row_id == 1
        signals = _fetch_signals(tmp_db)
        assert len(signals) == 1
        assert signals[0]["symbol"] == "BTCUSDT"
        assert signals[0]["price"] == 65000.0
        conn.close()

    def test_fetch_limit(self, seeded_db: Path) -> None:
        signals = _fetch_signals(seeded_db, limit=2)
        assert len(signals) == 2

    def test_fetch_order_newest_first(self, seeded_db: Path) -> None:
        signals = _fetch_signals(seeded_db)
        assert signals[0]["timestamp"] > signals[-1]["timestamp"]

    def test_fetch_nonexistent_db(self, tmp_path: Path) -> None:
        signals = _fetch_signals(tmp_path / "nope.db")
        assert signals == []


# ---------------------------------------------------------------------------
# FastAPI endpoint tests
# ---------------------------------------------------------------------------


class TestWebhookEndpoint:
    """Test POST /webhook and GET /health."""

    def test_health(self, client) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_valid_webhook(self, client) -> None:
        resp = client.post("/webhook", json=VALID_PAYLOAD)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "received"
        assert data["id"] == 1

    def test_second_webhook_increments_id(self, client) -> None:
        client.post("/webhook", json=VALID_PAYLOAD)
        resp = client.post("/webhook", json={**VALID_PAYLOAD, "symbol": "ETHUSDT"})
        assert resp.json()["id"] == 2

    def test_missing_field(self, client) -> None:
        incomplete = {"symbol": "BTCUSDT", "side": "buy"}
        resp = client.post("/webhook", json=incomplete)
        assert resp.status_code == 422

    def test_invalid_side(self, client) -> None:
        bad = {**VALID_PAYLOAD, "side": "hold"}
        resp = client.post("/webhook", json=bad)
        assert resp.status_code == 422

    def test_negative_price(self, client) -> None:
        bad = {**VALID_PAYLOAD, "price": -100}
        resp = client.post("/webhook", json=bad)
        assert resp.status_code == 422

    def test_zero_price(self, client) -> None:
        bad = {**VALID_PAYLOAD, "price": 0}
        resp = client.post("/webhook", json=bad)
        assert resp.status_code == 422

    def test_webhook_with_telegram(self, tmp_db: Path) -> None:
        from fastapi.testclient import TestClient

        api = create_app(
            db_path=tmp_db,
            telegram_token="fake-token",
            telegram_chat_id="12345",
        )
        tc = TestClient(api)
        with patch("webhook_bridge._send_telegram", return_value=True) as mock_tg:
            resp = tc.post("/webhook", json=VALID_PAYLOAD)
            assert resp.status_code == 200
            mock_tg.assert_called_once()


# ---------------------------------------------------------------------------
# CLI command tests
# ---------------------------------------------------------------------------


class TestCLIHistory:
    """Test the 'history' command."""

    def test_history_shows_signals(self, seeded_db: Path) -> None:
        result = runner.invoke(app, ["history", "--db", str(seeded_db)])
        assert result.exit_code == 0
        assert "BTCUSDT" in result.output
        assert "ETHUSDT" in result.output

    def test_history_no_db(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["history", "--db", str(tmp_path / "nope.db")])
        assert result.exit_code == 1


class TestCLIExport:
    """Test the 'export' command."""

    def test_export_stdout(self, seeded_db: Path) -> None:
        result = runner.invoke(app, ["export", "--db", str(seeded_db)])
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        assert lines[0] == "date,symbol,side,entry_price,exit_price,quantity,pnl,fees"
        assert len(lines) == 5  # header + 4 signals

    def test_export_csv_format(self, seeded_db: Path) -> None:
        result = runner.invoke(app, ["export", "--db", str(seeded_db)])
        reader = csv.DictReader(result.output.strip().split("\n"))
        rows = list(reader)
        assert rows[0]["symbol"] == "BTCUSDT"
        assert rows[0]["side"] == "LONG"  # buy → LONG
        assert rows[1]["side"] == "SHORT"  # sell → SHORT

    def test_export_to_file(self, seeded_db: Path, tmp_path: Path) -> None:
        out = tmp_path / "out.csv"
        result = runner.invoke(app, ["export", "--db", str(seeded_db), "-o", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        lines = out.read_text().strip().split("\n")
        assert len(lines) == 5

    def test_export_no_db(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["export", "--db", str(tmp_path / "nope.db")])
        assert result.exit_code == 1


class TestCLIStats:
    """Test the 'stats' command."""

    def test_stats_shows_summary(self, seeded_db: Path) -> None:
        result = runner.invoke(app, ["stats", "--db", str(seeded_db)])
        assert result.exit_code == 0
        assert "Total signals" in result.output
        assert "smc_reversal" in result.output
        assert "BTCUSDT" in result.output

    def test_stats_no_db(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["stats", "--db", str(tmp_path / "nope.db")])
        assert result.exit_code == 1
