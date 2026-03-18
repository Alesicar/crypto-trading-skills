# Crypto Trading Skills for Claude Code

> Production-grade Claude Code skills for crypto trading, DeFi analysis, and algorithmic strategy development. Built by a futures trader running live infrastructure, not a tutorial writer.

## What This Is

A collection of **Claude Code skills** that give Claude deep knowledge of crypto trading, Pine Script development, on-chain analytics, and portfolio management. Each skill is a self-contained markdown file that plugs directly into Claude Code's skill system.

These skills encode real trading knowledge — Smart Money Concepts, funding rate arbitrage, risk governance, position sizing — so Claude Code can generate production-quality trading tools instead of generic boilerplate.

## Pine Script v6 Generator CLI

The flagship tool: a Typer CLI that generates, validates, and analyzes TradingView Pine Script v6 strategies using Claude with deep SMC knowledge baked into every prompt.

### Installation

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your-key-here
```

### Commands

#### `generate` — Natural Language → Pine Script v6

```bash
# Basic generation (prints to terminal)
python pinescript_ai.py generate "15m SMC reversal with CHoCH + Order Block in discount zone"

# Save to file
python pinescript_ai.py generate "BTC scalper using RSI divergence" --output strategies/rsi_scalper.pine

# Use a different model
python pinescript_ai.py generate "Multi-TF trend follower" --model claude-sonnet-4-20250514

# Skip post-generation validation
python pinescript_ai.py generate "EMA crossover with volume" --output ema.pine --no-validate
```

The system prompt contains 2000+ words of genuine Pine Script v6 syntax rules, Smart Money Concepts patterns (CHoCH, BOS, Order Blocks, FVG, liquidity sweeps), risk management templates, and anti-repainting guards. Every generated strategy includes `barstate.isconfirmed`, proper `request.security()` with `lookahead_off`, and realistic commission/slippage defaults.

#### `validate` — Static Analysis for Pine Script

```bash
python pinescript_ai.py validate my_strategy.pine
```

Checks for real bugs traders actually hit:
- Missing `//@version=6` declaration
- Deprecated functions (`security()` → `request.security()`, `study()` → `indicator()`)
- `barmerge.lookahead_on` (future data leakage)
- Bracket/parenthesis imbalance
- `strategy.exit()` IDs not matching `strategy.entry()` IDs
- Missing `barstate.isconfirmed` on entries (repainting risk)
- No `alertcondition()` or `alert()` in strategies
- Bare `tickerid` instead of `syminfo.tickerid`
- Variable names shadowing Pine built-ins
- `calc_on_every_tick=true` (unrealistic backtests)

Output is a Rich table with severity (ERROR/WARN/INFO) and line numbers.

#### `explain` — Strategy Analysis

```bash
python pinescript_ai.py explain examples/smc_reversal.pine
```

Returns structured analysis:
- What the strategy does (2-3 sentences)
- Entry conditions (bullet points)
- Exit conditions
- Risk management approach
- Recommended timeframe and market
- Key parameters to tune with suggested ranges

#### `templates` — 7 Preset Strategy Prompts

```bash
python pinescript_ai.py templates
```

Shows Rich-formatted panels for each template:

| # | Template | Description |
|---|----------|-------------|
| 1 | **SMC Reversal** | CHoCH + OB in discount zone |
| 2 | **SMC Continuation** | BOS + FVG entry |
| 3 | **Liquidity Sweep Reversal** | Sweep + CHoCH + OB |
| 4 | **Multi-TF Confluence** | 1H bias + 15m entry |
| 5 | **EMA Volume Breakout** | 20/50 cross + 1.5x volume |
| 6 | **Funding Rate Scalper** | RSI extreme + structural level |
| 7 | **Confluence Scorer** | Point system, enter at score >= 4 |

Each template includes the exact prompt to copy-paste into `generate`.

#### `backtest-summary` — Theoretical Performance Estimation

```bash
python pinescript_ai.py backtest-summary examples/confluence_scorer.pine
```

Analyzes strategy logic and estimates:
- Expected win rate range
- Profit factor estimate
- Ideal market conditions
- Weaknesses and failure modes
- Parameter optimization suggestions

## Skills

| Skill | Description | Status |
|-------|-------------|--------|
| **Pine Script Generator** | Generate Pine Script v6 strategies from natural language. Deep SMC knowledge: CHoCH, BOS, Order Blocks, FVG, liquidity sweeps. Outputs compilable code with proper `strategy()` structure, alerts, and risk management. | ✅ Ready |
| **Funding Rate Scanner** | Build funding rate monitoring tools across exchanges using CCXT. Spot arbitrage opportunities, calculate annualized rates, flag divergences. | 🔜 Next |
| **Trade Journal Analyzer** | Analyze trade logs and generate performance reports — Sharpe ratio, max drawdown, profit factor, rolling win rate, strategy attribution. Works with CSV and SQLite. | 🔜 Planned |
| **On-Chain Whale Tracker** | Query blockchain APIs, parse whale transactions, detect accumulation/distribution patterns, flag significant wallet movements. | 🔜 Planned |
| **DeFi Yield Analyzer** | Evaluate yield farming opportunities — APR/APY calculation, impermanent loss estimation, TVL trend analysis, protocol risk scoring. | 🔜 Planned |
| **Risk Governor** | Build portfolio risk management systems — position sizing, correlation monitoring, drawdown protection, circuit breakers, strategy auto-kill logic. | 🔜 Planned |

## Example Strategies

- **`examples/smc_reversal.pine`** — CHoCH + Order Block entry with ATR stops, discount/premium zone filter
- **`examples/confluence_scorer.pine`** — Point-based multi-factor system (CHoCH +2, OB +2, FVG +1, zone +1, volume +1, HTF +1), enter at configurable threshold

## Why These Skills Exist

Most AI-generated trading code is surface-level — it compiles but doesn't reflect how real trading systems work. These skills are built from experience running live algorithmic trading infrastructure:

- **Pine Script strategies** tested through multi-month paper validation windows
- **Risk governance** with circuit breakers, correlation monitoring, and strategy survival rules
- **Funding rate arbitrage** with real spread calculations and execution timing
- **Portfolio management** with proper attribution, drawdown tracking, and regime detection

The goal is to make Claude Code a useful pair programmer for traders who know what they're doing, not a toy that outputs generic Moving Average crossovers.

## Built With

- Claude Code for skill development and testing
- Anthropic API (Claude) for generation, explanation, and analysis
- Python + Typer + Rich for the CLI
- TradingView / Pine Script v6 for strategy execution

## Contributing

PRs welcome, especially for:
- New exchange-specific skills (Bybit, Binance, Hyperliquid)
- Additional SMC pattern implementations
- Backtesting and optimization skills
- DeFi protocol-specific analyzers

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT — use these skills however you want.

---

*Built on train commutes in Slovenia. Skills are extracted from production trading systems, not tutorials.*
