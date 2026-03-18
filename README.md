# Crypto Trading Skills for Claude Code

> Production-grade Claude Code skills for crypto trading, DeFi analysis, and algorithmic strategy development. Built by a futures trader running live infrastructure, not a tutorial writer.

## What This Is

A collection of **Claude Code skills** that give Claude deep knowledge of crypto trading, Pine Script development, on-chain analytics, and portfolio management. Each skill is a self-contained markdown file that plugs directly into Claude Code's skill system.

These skills encode real trading knowledge — Smart Money Concepts, funding rate arbitrage, risk governance, position sizing — so Claude Code can generate production-quality trading tools instead of generic boilerplate.

## Skills

| Skill | Description | Status |
|-------|-------------|--------|
| **Pine Script Generator** | Generate Pine Script v6 strategies from natural language. Deep SMC knowledge: CHoCH, BOS, Order Blocks, FVG, liquidity sweeps. Outputs compilable code with proper `strategy()` structure, alerts, and risk management. | ✅ Ready |
| **Funding Rate Scanner** | Build funding rate monitoring tools across exchanges using CCXT. Spot arbitrage opportunities, calculate annualized rates, flag divergences. | 🔜 Next |
| **Trade Journal Analyzer** | Analyze trade logs and generate performance reports — Sharpe ratio, max drawdown, profit factor, rolling win rate, strategy attribution. Works with CSV and SQLite. | 🔜 Planned |
| **On-Chain Whale Tracker** | Query blockchain APIs, parse whale transactions, detect accumulation/distribution patterns, flag significant wallet movements. | 🔜 Planned |
| **DeFi Yield Analyzer** | Evaluate yield farming opportunities — APR/APY calculation, impermanent loss estimation, TVL trend analysis, protocol risk scoring. | 🔜 Planned |
| **Risk Governor** | Build portfolio risk management systems — position sizing, correlation monitoring, drawdown protection, circuit breakers, strategy auto-kill logic. | 🔜 Planned |

## Installation

Clone this repo into your Claude Code skills directory:

```bash
git clone https://github.com/YOUR_USERNAME/crypto-trading-skills.git
```

Then reference individual skills in your Claude Code workflow:

```
Read the skill at crypto-trading-skills/skills/pinescript-generator/SKILL.md and use it to generate a 15-minute SMC reversal strategy with CHoCH entries and Order Block confirmation.
```

## Example: Pine Script Generation

**Prompt:**
```
Generate a Pine Script v6 strategy: 15-minute timeframe, enter long on bullish CHoCH with Order Block confirmation from 1H, use ATR-based stop loss at 1.5x ATR below entry, take profit at 2R. Include alert conditions.
```

**Output:** A compilable Pine Script v6 strategy with proper structure, MTF confirmation via `request.security()`, ATR-based risk management, and TradingView alert conditions — ready to paste into TradingView and run.

## Why These Skills Exist

Most AI-generated trading code is surface-level — it compiles but doesn't reflect how real trading systems work. These skills are built from experience running live algorithmic trading infrastructure:

- **Pine Script strategies** tested through multi-month paper validation windows
- **Risk governance** with circuit breakers, correlation monitoring, and strategy survival rules
- **Funding rate arbitrage** with real spread calculations and execution timing
- **Portfolio management** with proper attribution, drawdown tracking, and regime detection

The goal is to make Claude Code a useful pair programmer for traders who know what they're doing, not a toy that outputs generic Moving Average crossovers.

## Built With

- Claude Code for skill development and testing
- Python + CCXT for exchange connectivity
- SQLite for trade data persistence
- TradingView / Pine Script v6 for strategy execution

## Contributing

PRs welcome, especially for:
- New exchange-specific skills (Bybit, Binance, Hyperliquid)
- Additional SMC pattern implementations
- Backtesting and optimization skills
- DeFi protocol-specific analyzers

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Related

- **[SMC Scanner](https://smc-field-guide.netlify.app)** — Real-time Smart Money Concepts alerts delivered via Telegram. If you find the Pine Script skill useful, you might want live SMC signals.

## License

MIT — use these skills however you want.

---

*Built on train commutes in Slovenia. Skills are extracted from production trading systems, not tutorials.*
