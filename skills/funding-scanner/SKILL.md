# Funding Rate Scanner

## Overview
CLI tool for analyzing crypto perpetual futures funding rates across exchanges using CCXT.

## Funding Rate Concepts

### What Are Funding Rates?
Perpetual futures contracts have no expiry date. To keep the perpetual price anchored to spot price, exchanges use a **funding rate mechanism** — periodic payments between long and short traders.

- **Positive funding rate**: Longs pay shorts. The perp trades at a premium to spot (bullish sentiment). Shorting earns you funding.
- **Negative funding rate**: Shorts pay longs. The perp trades at a discount to spot (bearish sentiment). Going long earns you funding.

### Funding Intervals
- **Bybit**: Every 8 hours (00:00, 08:00, 16:00 UTC)
- **Binance**: Every 8 hours (00:00, 08:00, 16:00 UTC)
- **OKX**: Every 8 hours (00:00, 08:00, 16:00 UTC)

### Annualized Rate Calculation
```
annualized_rate = current_rate × 3 (per day) × 365 (per year)
```
A 0.01% funding rate = 0.03% daily = 10.95% annualized.

### Extreme Funding Rates
- Above **+25% annualized**: Market is extremely bullish on this pair. Shorting earns significant funding.
- Below **-25% annualized**: Market is extremely bearish. Going long earns significant funding.
- Extreme rates often precede mean reversion — they indicate crowded positioning.

### Funding Rate Arbitrage
Funding rate arbitrage exploits differences in funding rates for the same asset across exchanges:

1. **Identify spread**: Same pair has different funding rates on two exchanges.
2. **Go long** on the exchange with the lower (or more negative) rate.
3. **Go short** on the exchange with the higher (or more positive) rate.
4. **Collect the spread**: You earn the difference in funding rates with delta-neutral exposure.

A spread above **10% annualized** is generally considered actionable after accounting for trading fees and slippage.

### Risks
- **Liquidation risk**: Funding arbitrage requires margin on both exchanges. Sudden price moves can trigger liquidation on one leg.
- **Withdrawal delays**: Moving capital between exchanges takes time.
- **Rate changes**: Funding rates update every 8 hours and can reverse quickly.
- **Basis risk**: Execution prices may differ between exchanges.

## Commands

### `scan`
Pull current funding rates for all USDT perpetual pairs from an exchange.
```bash
python funding_scanner.py scan                    # Bybit, all pairs
python funding_scanner.py scan --exchange binance  # Binance
python funding_scanner.py scan --top 20            # Top 20 by absolute rate
python funding_scanner.py scan --watch             # Auto-refresh every 60s
python funding_scanner.py scan --json              # JSON output for piping
```

### `history`
View last 30 funding rate data points for a specific symbol.
```bash
python funding_scanner.py history BTC/USDT:USDT
python funding_scanner.py history ETH/USDT:USDT --exchange binance
```

### `arbitrage`
Compare funding rates across Bybit, Binance, and OKX to find arbitrage opportunities.
```bash
python funding_scanner.py arbitrage
python funding_scanner.py arbitrage --top 10
python funding_scanner.py arbitrage --json
```

## No API Keys Required
All commands use public market data endpoints. No exchange API keys needed.
