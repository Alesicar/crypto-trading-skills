# Pine Script AI — Generate, Validate & Analyze TradingView Strategies

> Production-grade CLI for generating, validating, and analyzing TradingView Pine Script v6 strategies using Claude with deep Smart Money Concepts knowledge.

## Project Structure

```
crypto-trading-skills/
├── pinescript_ai.py              # Pine Script generator CLI (Typer app)
├── funding_scanner.py            # Funding rate scanner CLI (CCXT + Typer)
├── trade_journal.py              # Trade journal analyzer CLI (Typer)
├── sample_trades.csv             # 50 sample crypto futures trades
├── pyproject.toml                # pip-installable package config
├── requirements.txt              # Python dependencies
├── examples/
│   ├── smc_reversal.pine         # CHoCH + Order Block in discount zone
│   ├── mtf_confluence.pine       # 1H bias + 15m CHoCH/OB + RSI filter
│   └── confluence_scorer.pine    # Point system (CHoCH+2, OB+2, FVG+1, zone+1, RSI+1, vol+1)
├── skills/
│   ├── pinescript-generator/
│   │   └── SKILL.md              # Pine Script generator skill docs
│   ├── funding-scanner/
│   │   └── SKILL.md              # Funding rate concepts & usage
│   └── trade-journal/
│       └── SKILL.md              # Trade analysis concepts & usage
├── tests/
│   └── test_trade_journal.py     # Trade journal unit tests
├── .github/
│   └── workflows/
│       └── ci.yml                # Validates all example .pine files on push
├── CLAUDE.md                     # Project instructions for Claude Code
└── README.md
```

## Installation

```bash
# From source
pip install -e .

# Or just install dependencies
pip install -r requirements.txt
```

Set your API key for generate/explain/backtest-summary commands:

```bash
export ANTHROPIC_API_KEY=your-key-here
```

## Commands

### `validate` — Static Analysis (offline, no API key needed)

```bash
python pinescript_ai.py validate examples/smc_reversal.pine
python pinescript_ai.py validate examples/mtf_confluence.pine
python pinescript_ai.py validate examples/confluence_scorer.pine
```

Checks for:
- Missing `//@version=6` declaration
- Deprecated functions (`security()` → `request.security()`, `study()` → `indicator()`)
- `barmerge.lookahead_on` (future data leakage)
- Bracket/parenthesis imbalance
- `strategy.exit()` IDs not matching `strategy.entry()` IDs
- Missing `barstate.isconfirmed` (repainting risk)
- No `alertcondition()` or `alert()` calls
- Bare `tickerid` instead of `syminfo.tickerid`
- Variable names shadowing Pine built-ins
- `calc_on_every_tick=true` (unrealistic backtests)

### `generate` — Natural Language → Pine Script v6

```bash
# Print to terminal
python pinescript_ai.py generate "15m SMC reversal with CHoCH + OB in discount zone"

# Save to file
python pinescript_ai.py generate "BTC scalper using RSI divergence" -o strategies/rsi_scalper.pine

# Use a different model
python pinescript_ai.py generate "EMA crossover with volume" --model claude-sonnet-4-20250514
```

### `explain` — Structured Strategy Analysis

```bash
python pinescript_ai.py explain examples/smc_reversal.pine
```

Returns entry/exit conditions, risk management approach, recommended timeframe, and key parameters to tune.

### `backtest-summary` — Theoretical Performance Estimation

```bash
python pinescript_ai.py backtest-summary examples/confluence_scorer.pine
```

Estimates win rate, profit factor, ideal market conditions, and weaknesses.

### `templates` — 7 Preset Strategy Prompts

```bash
python pinescript_ai.py templates
```

## Example Strategies

### 1. SMC Reversal (`examples/smc_reversal.pine`)

CHoCH detection against prevailing trend + Order Block entry in the discount zone. ATR-based stop loss below the OB, 2R take-profit target. Includes alertconditions and full commenting.

- **Entry**: Bullish CHoCH → price retraces into bullish OB → discount zone filter
- **Stop**: Below OB bottom - ATR buffer
- **Target**: 2R from entry
- **Best on**: 15m–1H crypto

### 2. MTF Confluence (`examples/mtf_confluence.pine`)

Uses 1H market structure (via `request.security` with `lookahead_off`) to determine trend bias. Enters on 15m CHoCH + Order Block setups aligned with HTF direction. RSI filter prevents entries in overbought/oversold extremes.

- **Entry**: HTF bullish + LTF bullish CHoCH + OB retracement + RSI not overbought
- **Stop**: Structural — beyond the Order Block with ATR buffer
- **Target**: 2R from entry
- **Best on**: 15m chart with 1H HTF

### 3. Confluence Scorer (`examples/confluence_scorer.pine`)

Point-based multi-factor system. Awards points for: CHoCH (+2), Order Block (+2), FVG (+1), premium/discount zone (+1), RSI (+1), volume (+1). Enters when score reaches configurable threshold (default: 4/8). Labels on chart show score breakdown at each entry.

- **Entry**: Score >= threshold (configurable per side)
- **Stop**: ATR-based (1.5x ATR below/above entry)
- **Target**: 2R from entry
- **Best on**: 15m–1H crypto

## Key Conventions

All generated and example strategies follow these rules:

- **Pine Script v6** (`//@version=6`) — always
- **`barstate.isconfirmed`** on all entries — prevents repainting
- **`barmerge.lookahead_off`** on all `request.security()` — prevents future data leakage
- **Realistic costs**: 0.06% commission (Binance/Bybit taker), 2-tick slippage
- **`calc_on_every_tick=false`** — prevents intra-bar recalculation
- **`process_orders_on_close=false`** — prevents close-price lookahead

## CI

GitHub Actions runs `python pinescript_ai.py validate` against all example `.pine` files on every push. See `.github/workflows/ci.yml`.

---

## Funding Rate Scanner (`funding_scanner.py`)

> Real-time crypto perpetual futures funding rate analysis across exchanges. No API keys required.

### `scan` — Current Funding Rates

```bash
python funding_scanner.py scan                          # All Bybit USDT perps
python funding_scanner.py scan --exchange binance       # Binance
python funding_scanner.py scan --top 20                 # Top 20 by absolute rate
python funding_scanner.py scan --watch                  # Auto-refresh every 60s
python funding_scanner.py scan --json                   # JSON output for piping
python funding_scanner.py scan --exchange okx --top 10  # OKX top 10
```

Color coding: green = positive (shorts earn), red = negative (longs earn). Pairs above 25% or below -25% annualized are flagged.

### `history` — Funding Rate History

```bash
python funding_scanner.py history BTC/USDT:USDT
python funding_scanner.py history ETH/USDT:USDT --exchange binance
```

Shows last 30 funding rate data points with visual bar chart.

### `arbitrage` — Cross-Exchange Arbitrage

```bash
python funding_scanner.py arbitrage                # Scan Bybit + Binance + OKX
python funding_scanner.py arbitrage --top 10       # Top 10 opportunities
python funding_scanner.py arbitrage --json         # JSON output
```

Flags any spread above 10% annualized between exchanges.

---

## Trade Journal Analyzer (`trade_journal.py`)

> Analyze crypto trade performance from CSV journals with full metrics dashboard.

### CSV Format

```csv
date,symbol,side,entry_price,exit_price,quantity,pnl,fees
2025-01-15,BTC,LONG,42000.00,43500.00,0.05,75.00,2.10
```

A sample file with 50 realistic trades is included: `sample_trades.csv`

### `analyze` — Full Performance Dashboard

```bash
python trade_journal.py analyze sample_trades.csv
```

Outputs: total trades, win rate, profit factor, total P&L, average win/loss, largest win/loss, max consecutive wins/losses, Sharpe ratio, max drawdown with dates, R-multiple distribution, monthly breakdown, performance by symbol/side/day of week.

### `equity` — ASCII Equity Curve

```bash
python trade_journal.py equity sample_trades.csv
```

### `compare` — Side-by-Side Comparison

```bash
python trade_journal.py compare strategy_a.csv strategy_b.csv
```

### `export` — Markdown Report

```bash
python trade_journal.py export sample_trades.csv -o report.md
```

### Tests

```bash
pytest tests/test_trade_journal.py -v
```

## License

MIT
