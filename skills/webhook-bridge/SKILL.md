# Webhook Bridge — TradingView Alert Receiver

## Overview

`webhook_bridge.py` is a FastAPI server that receives TradingView webhook alerts over HTTP, logs them to a SQLite database, and optionally forwards them to Telegram. It completes the full automation loop:

```
pinescript_ai generates strategies
  → user deploys to TradingView
    → webhook_bridge catches signals and logs them
      → trade_journal analyzes performance
```

## TradingView Webhook Setup

### 1. Get a Public URL

TradingView webhooks need a publicly reachable URL. Options:

- **VPS/Cloud**: Deploy on a server with a public IP
- **ngrok**: For local development — `ngrok http 8080` gives you a public URL
- **Cloudflare Tunnel**: `cloudflared tunnel --url http://localhost:8080`

### 2. Create an Alert in TradingView

1. Open your chart with the strategy deployed
2. Click **Alerts** (clock icon) → **Create Alert**
3. Set **Condition** to your strategy's alert condition
4. Under **Notifications**, enable **Webhook URL**
5. Enter your server URL: `https://your-domain.com/webhook`
6. In the **Message** field, paste the JSON payload (see below)
7. Click **Create**

### 3. JSON Payload Format

TradingView sends the alert message body as-is to your webhook URL. Use this exact JSON format in the alert message field:

```json
{
  "symbol": "{{ticker}}",
  "side": "buy",
  "price": {{close}},
  "strategy_name": "smc_reversal",
  "message": "CHoCH detected on {{interval}}"
}
```

#### TradingView Placeholders

| Placeholder      | Description                        |
|------------------|------------------------------------|
| `{{ticker}}`     | Symbol name (e.g., BTCUSDT)       |
| `{{close}}`      | Current close price                |
| `{{open}}`       | Current open price                 |
| `{{high}}`       | Current high                       |
| `{{low}}`        | Current low                        |
| `{{volume}}`     | Current volume                     |
| `{{interval}}`   | Chart timeframe (e.g., 15)        |
| `{{time}}`       | Bar time in UTC                    |
| `{{exchange}}`   | Exchange name                      |

#### Payload Fields

| Field           | Type   | Required | Description                          |
|-----------------|--------|----------|--------------------------------------|
| `symbol`        | string | yes      | Trading pair (e.g., "BTCUSDT")      |
| `side`          | string | yes      | `"buy"` or `"sell"`                  |
| `price`         | number | yes      | Entry price (must be > 0)            |
| `strategy_name` | string | yes      | Strategy identifier                  |
| `message`       | string | yes      | Human-readable signal description    |

#### Buy vs Sell Alerts

For strategies with both long and short entries, create two separate alerts:

**Long entry alert message:**
```json
{
  "symbol": "{{ticker}}",
  "side": "buy",
  "price": {{close}},
  "strategy_name": "smc_reversal",
  "message": "Long entry — CHoCH + OB in discount zone"
}
```

**Short entry alert message:**
```json
{
  "symbol": "{{ticker}}",
  "side": "sell",
  "price": {{close}},
  "strategy_name": "smc_reversal",
  "message": "Short entry — CHoCH + OB in premium zone"
}
```

## Commands

### `serve` — Start the Webhook Server

```bash
python webhook_bridge.py serve                              # Default port 8080
python webhook_bridge.py serve --port 9090                  # Custom port
python webhook_bridge.py serve --db signals.db              # Custom database
python webhook_bridge.py serve --telegram-token BOT_TOKEN --telegram-chat-id CHAT_ID
```

### `history` — View Recent Signals

```bash
python webhook_bridge.py history                # Last 20 signals
python webhook_bridge.py history --last 50      # Last 50 signals
python webhook_bridge.py history --db signals.db
```

### `export` — Dump to CSV (trade_journal.py compatible)

```bash
python webhook_bridge.py export                         # Print CSV to stdout
python webhook_bridge.py export -o signals.csv          # Save to file
python webhook_bridge.py export | python trade_journal.py analyze /dev/stdin
```

Output CSV format matches trade_journal.py expectations:
```
date,symbol,side,entry_price,exit_price,quantity,pnl,fees
```

### `stats` — Quick Summary

```bash
python webhook_bridge.py stats
```

Shows: total signals, signals per strategy, signals per symbol, signals per day, last signal time.

## Telegram Integration

To forward signals to Telegram:

1. Create a bot via [@BotFather](https://t.me/BotFather) and get the token
2. Get your chat ID by messaging [@userinfobot](https://t.me/userinfobot)
3. Start the server with both flags:

```bash
python webhook_bridge.py serve \
  --telegram-token "123456:ABC-DEF..." \
  --telegram-chat-id "-1001234567890"
```

Each signal is sent as a formatted Telegram message with side arrow, symbol, price, strategy, and message.

## Testing the Webhook Locally

```bash
# Terminal 1: start the server
python webhook_bridge.py serve

# Terminal 2: send a test webhook
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSDT",
    "side": "buy",
    "price": 65000.00,
    "strategy_name": "smc_reversal",
    "message": "CHoCH detected on 15m"
  }'
```

## Database Schema

SQLite database (`trades.db` by default):

```sql
CREATE TABLE signals (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp     TEXT NOT NULL,    -- ISO 8601 UTC
    symbol        TEXT NOT NULL,
    side          TEXT NOT NULL,    -- 'buy' or 'sell'
    price         REAL NOT NULL,
    strategy_name TEXT NOT NULL,
    message       TEXT NOT NULL
);
```
