# Trade Journal Analyzer

## Overview
CLI tool for analyzing crypto trade performance from CSV journal data.

## Trade Analysis Concepts

### Core Metrics

**Win Rate**
Percentage of trades that were profitable (net of fees). A win rate above 50% is not required for profitability — many successful strategies have 30-40% win rates with large R-multiples on winners.

**Profit Factor**
```
profit_factor = gross_profit / gross_loss
```
- **< 1.0**: Losing system
- **1.0 – 1.5**: Marginal edge
- **1.5 – 2.0**: Good edge
- **> 2.0**: Strong edge

**Sharpe Ratio**
Risk-adjusted return metric. Measures excess return per unit of risk (standard deviation).
```
sharpe = (mean_return / std_return) × sqrt(365)
```
- **< 0.5**: Poor risk-adjusted returns
- **0.5 – 1.0**: Acceptable
- **1.0 – 2.0**: Good
- **> 2.0**: Excellent

### Drawdown Analysis

**Maximum Drawdown**
The largest peak-to-trough decline in equity. Reported with dates showing when the peak and trough occurred.

Why it matters:
- Indicates worst-case scenario for account balance
- A 50% drawdown requires a 100% gain to recover
- Professional risk limit: typically 10-20% max drawdown

### R-Multiples

R-multiple normalizes trade outcomes by risk:
```
R = trade_pnl / average_loss
```
- **1R**: You made what you typically risk
- **2R**: You made twice your typical risk
- **-1R**: You lost your typical risk amount

Distribution of R-multiples reveals if your winners are big enough to compensate for losses.

### Performance Breakdowns

**By Symbol**: Identifies which assets you trade best. Over-concentration in one asset adds correlation risk.

**By Side (Long/Short)**: Reveals directional bias. Many traders perform significantly better on one side.

**By Day of Week**: Crypto trades 24/7 but volume/volatility patterns vary. Weekend trades often have different characteristics.

**Monthly Breakdown**: Shows consistency over time. Large variance between months indicates strategy instability.

## CSV Format
```
date,symbol,side,entry_price,exit_price,quantity,pnl,fees
2025-01-15,BTC,LONG,42000.00,43500.00,0.05,75.00,2.10
```

| Column | Type | Description |
|--------|------|-------------|
| date | YYYY-MM-DD | Trade close date |
| symbol | string | Asset symbol (BTC, ETH, SOL, etc.) |
| side | LONG/SHORT | Trade direction |
| entry_price | float | Entry price |
| exit_price | float | Exit price |
| quantity | float | Position size in base asset |
| pnl | float | Realized profit/loss (before fees) |
| fees | float | Total fees paid |

## Commands

### `analyze`
Full performance dashboard with all metrics.
```bash
python trade_journal.py analyze sample_trades.csv
```

### `equity`
ASCII equity curve visualization.
```bash
python trade_journal.py equity sample_trades.csv
```

### `compare`
Side-by-side comparison of two trade journals.
```bash
python trade_journal.py compare strategy_a.csv strategy_b.csv
```

### `export`
Formatted markdown report.
```bash
python trade_journal.py export sample_trades.csv -o report.md
```
