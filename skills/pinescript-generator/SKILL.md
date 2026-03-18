# Pine Script v6 Generator — Claude Code Skill

> Full reference for generating production-grade Pine Script v6 strategies with Smart Money Concepts, risk management, and proper TradingView structure.

## Skill Overview

This skill enables Claude Code to generate, validate, and analyze TradingView Pine Script v6 strategies. It encodes deep knowledge of Pine Script syntax, Smart Money Concepts (SMC) trading patterns, risk management frameworks, and common pitfalls that cause repainting, lookahead bias, or compilation errors.

## CLI Tool

The `pinescript_ai.py` CLI provides five commands:

| Command | Description |
|---------|-------------|
| `generate` | Natural language → compilable Pine Script v6 |
| `validate` | Static analysis of .pine files for bugs and bad practices |
| `explain` | Structured analysis of what a strategy does |
| `templates` | 7 preset strategy prompts for common setups |
| `backtest-summary` | Theoretical performance estimation |

---

## Pine Script v6 Syntax Reference

### Version Declaration
Every Pine Script file MUST start with the version annotation:
```pine
//@version=6
```
This is a compiler directive, not a comment. Without it, TradingView defaults to an older version and many v6 features break.

### Strategy Declaration
```pine
strategy("Strategy Name", overlay=true,
         initial_capital=10000,
         default_qty_type=strategy.percent_of_equity,
         default_qty_value=100,
         commission_type=strategy.commission.percent,
         commission_value=0.06,
         slippage=2,
         calc_on_every_tick=false,
         process_orders_on_close=false,
         pyramiding=0)
```

Key parameters:
- `initial_capital=10000` — realistic starting capital for crypto
- `commission_value=0.06` — Bybit/Binance taker fee (0.06%)
- `slippage=2` — 2 ticks of slippage, realistic for BTC/ETH on major exchanges
- `calc_on_every_tick=false` — CRITICAL: prevents intra-bar recalculation
- `process_orders_on_close=false` — prevents lookahead from close-price ordering
- `pyramiding=0` — no additional entries while in a position (default)

### Indicator Declaration
```pine
indicator("Indicator Name", overlay=true, max_bars_back=500)
```
Use `indicator()` — never `study()` which was deprecated in v5.

### Variable Types and Declaration

Pine Script v6 types:
- `float` — decimal numbers (default for most values)
- `int` — integers
- `bool` — true/false
- `string` — text
- `color` — color values
- `label`, `line`, `box`, `table` — drawing types
- `array<type>` — typed arrays

```pine
// Reinitializes every bar (no persistence)
float my_val = close

// Persists across bars — only initializes on bar 0
var float entry_price = na
var int trade_dir = 0
var bool in_trade = false

// Updates on every tick (real-time only, rare use)
varip float tick_count = 0
```

The `var` keyword is critical. Without it, your variable resets to its initial value on every single bar, which is the #1 source of bugs in Pine Script strategies.

### Namespace Reference

All built-in functions are namespaced in v6:

**Technical Analysis — `ta.*`**
```pine
ta.sma(source, length)        // Simple Moving Average
ta.ema(source, length)        // Exponential Moving Average
ta.rsi(source, length)        // Relative Strength Index
ta.atr(length)                // Average True Range
ta.macd(source, fast, slow, signal)  // MACD
ta.crossover(a, b)            // a crosses above b
ta.crossunder(a, b)           // a crosses below b
ta.highest(source, length)    // Highest value in period
ta.lowest(source, length)     // Lowest value in period
ta.pivothigh(source, leftbars, rightbars)  // Swing high detection
ta.pivotlow(source, leftbars, rightbars)   // Swing low detection
ta.change(source)             // Difference from previous bar
ta.valuewhen(condition, source, occurrence)  // Value when condition was true
ta.barssince(condition)        // Bars since condition was true
ta.stoch(close, high, low, length)  // Stochastic
ta.bb(source, length, mult)   // Bollinger Bands
ta.vwap(source)               // VWAP
```

**Math — `math.*`**
```pine
math.abs(x)      math.max(a, b)     math.min(a, b)
math.round(x)    math.ceil(x)       math.floor(x)
math.log(x)      math.sqrt(x)       math.pow(base, exp)
math.sign(x)     math.avg(a, b...)
```

**String — `str.*`**
```pine
str.tostring(value)
str.format("{0} at {1}", ticker, price)
str.contains(source, target)
str.length(s)
```

**Request — `request.*`**
```pine
// Multi-timeframe data — ALWAYS use lookahead_off
htf_close = request.security(syminfo.tickerid, "60", close,
                              barmerge.gaps_off, barmerge.lookahead_off)

// Earnings, dividends, splits
request.earnings(syminfo.tickerid)
request.dividends(syminfo.tickerid)
```

### Input Functions
```pine
input.int(defval, title, minval, maxval, step, tooltip, group)
input.float(defval, title, minval, maxval, step, tooltip, group)
input.bool(defval, title, tooltip, group)
input.string(defval, title, options, tooltip, group)
input.source(defval, title, tooltip, group)
input.timeframe(defval, title, tooltip, group)
input.color(defval, title, tooltip, group)
```
Always use typed inputs — bare `input()` is deprecated in v6 context.

### Strategy Orders
```pine
// Entry
strategy.entry("Long", strategy.long, qty=position_size)
strategy.entry("Short", strategy.short, qty=position_size)

// Exit with stop and target
strategy.exit("Exit Long", from_entry="Long", stop=sl_price, limit=tp_price)
strategy.exit("Exit Short", from_entry="Short", stop=sl_price, limit=tp_price)

// Conditional close
strategy.close("Long", comment="Manual exit")

// Cancel pending
strategy.cancel_all()
```

The `from_entry` in `strategy.exit()` MUST match the `id` (first argument) in `strategy.entry()`. Mismatched IDs silently fail — no error, just no exit.

### Alert System
```pine
// For TradingView alert dialog
alertcondition(condition, title="Alert Name", message="Message text")

// For programmatic/webhook alerts
if condition
    alert("JSON or message", alert.freq_once_per_bar_close)
```

---

## Smart Money Concepts (SMC) — Pattern Library

### Market Structure: Swing Points

The foundation of all SMC analysis. A valid swing high has lower highs on both sides; a valid swing low has higher lows on both sides.

```pine
swingLen = input.int(5, "Swing Lookback")
var float lastSwingHigh = na
var float lastSwingLow = na
var int lastSwingHighBar = na
var int lastSwingLowBar = na

ph = ta.pivothigh(high, swingLen, swingLen)
pl = ta.pivotlow(low, swingLen, swingLen)

if not na(ph)
    lastSwingHigh := ph
    lastSwingHighBar := bar_index - swingLen
if not na(pl)
    lastSwingLow := pl
    lastSwingLowBar := bar_index - swingLen
```

Note: `ta.pivothigh()` returns the pivot value `swingLen` bars AFTER it occurred. The actual swing high bar is `bar_index - swingLen`.

### Change of Character (CHoCH)

A break against the prevailing trend — the first warning of reversal.

```pine
var int trend = 0  // 1 = bullish, -1 = bearish
var bool bullish_choch = false
var bool bearish_choch = false

// In a downtrend, bullish CHoCH = close breaks above last lower high
if trend == -1 and close > lastSwingHigh and barstate.isconfirmed
    bullish_choch := true
    trend := 0  // Neutral until confirmed by BOS

// In an uptrend, bearish CHoCH = close breaks below last higher low
if trend == 1 and close < lastSwingLow and barstate.isconfirmed
    bearish_choch := true
    trend := 0
```

CHoCH alone is NOT an entry signal. It's a warning that the trend may be changing. Always combine with Order Block, FVG, or other confirmation.

### Break of Structure (BOS)

A break with the trend — confirms continuation or validates a reversal after CHoCH.

```pine
var bool bullish_bos = false
var bool bearish_bos = false

// Bullish BOS: price makes new higher high
if trend >= 0 and close > lastSwingHigh and barstate.isconfirmed
    bullish_bos := true
    trend := 1

// Bearish BOS: price makes new lower low
if trend <= 0 and close < lastSwingLow and barstate.isconfirmed
    bearish_bos := true
    trend := -1
```

### Order Blocks (OB)

The last opposing candle before an impulsive move. This is where institutions placed orders.

```pine
var float ob_top = na
var float ob_bottom = na
var bool ob_active = false

// Find bullish OB after bullish BOS
if bullish_bos
    for i = 1 to 20
        if close[i] < open[i]  // Last bearish candle
            ob_top := high[i]
            ob_bottom := low[i]
            ob_active := true
            break

// Check if price returns to OB (entry zone)
ob_entry = ob_active and low <= ob_top and close >= ob_bottom

// OB mitigated (invalidated) when price closes below it
if ob_active and close < ob_bottom
    ob_active := false
```

Quality filters for Order Blocks:
- OB in discount zone (below 50% of range) for longs = higher probability
- OB that caused a BOS (not just any opposing candle) = institutional footprint
- Fresh (unmitigated) OBs are stronger than revisited ones
- OBs with high volume on the impulse candle = more significant

### Fair Value Gaps (FVG)

A 3-candle imbalance where price moved too fast, leaving an unfilled gap.

```pine
// Bullish FVG: gap up (current low > 2-bars-ago high)
bullish_fvg = low > high[2]
bullish_fvg_top = low          // Top of the gap
bullish_fvg_bottom = high[2]   // Bottom of the gap

// Bearish FVG: gap down (current high < 2-bars-ago low)
bearish_fvg = high < low[2]
bearish_fvg_top = low[2]       // Top of the gap
bearish_fvg_bottom = high      // Bottom of the gap

// FVG fill detection
var float fvg_zone_top = na
var float fvg_zone_bottom = na

if bullish_fvg
    fvg_zone_top := bullish_fvg_top
    fvg_zone_bottom := bullish_fvg_bottom

// Price enters the FVG zone
fvg_fill = not na(fvg_zone_bottom) and low <= fvg_zone_top and close >= fvg_zone_bottom
```

### Liquidity Sweeps

Equal highs/lows are liquidity pools where stop losses cluster. Smart money sweeps them.

```pine
// Detect equal highs (liquidity pool)
threshold = close * 0.001  // 0.1% threshold
var float eq_high_level = na
var int eq_high_count = 0

if not na(ph)
    if not na(eq_high_level) and math.abs(ph - eq_high_level) < threshold
        eq_high_count += 1
    else
        eq_high_level := ph
        eq_high_count := 1

// Sweep detection: price exceeds then closes back
high_swept = eq_high_count >= 2 and high > eq_high_level and close < eq_high_level
```

### Premium / Discount Zones

```pine
lookback = input.int(50, "Range Lookback")
range_high = ta.highest(high, lookback)
range_low = ta.lowest(low, lookback)
equilibrium = (range_high + range_low) / 2

in_discount = close < equilibrium  // Look for longs
in_premium = close > equilibrium   // Look for shorts

// Finer zones
deep_discount = close < range_low + (range_high - range_low) * 0.25
deep_premium = close > range_low + (range_high - range_low) * 0.75
```

---

## Risk Management Templates

### ATR-Based Dynamic Stops
```pine
atr_val = ta.atr(14)
atr_sl_mult = input.float(1.5, "SL ATR Multiple", step=0.1)
atr_tp_mult = input.float(3.0, "TP ATR Multiple", step=0.1)

long_sl = close - atr_val * atr_sl_mult
long_tp = close + atr_val * atr_tp_mult
short_sl = close + atr_val * atr_sl_mult
short_tp = close - atr_val * atr_tp_mult
```

### Structural Stop Loss
Place stops beyond the structure that justifies the trade:
```pine
// Long entry at bullish OB — stop below OB with buffer
long_structural_sl = ob_bottom - atr_val * 0.2

// Short entry at bearish OB — stop above OB with buffer
short_structural_sl = ob_top + atr_val * 0.2
```

### Risk-Based Position Sizing
```pine
risk_pct = input.float(1.0, "Risk % per Trade", step=0.1) / 100
risk_amount = strategy.equity * risk_pct
sl_distance = math.abs(close - stop_loss_price)
position_size = sl_distance > 0 ? risk_amount / sl_distance : 0
```

### Trailing Stop
```pine
// ATR trailing stop
var float trail_stop = na
if strategy.position_size > 0
    new_stop = close - atr_val * 2
    trail_stop := math.max(nz(trail_stop), new_stop)
else
    trail_stop := na
```

---

## Common Mistakes to Avoid

### 1. Missing `var` on Persistent Variables
```pine
// WRONG — resets to na every bar
float entry_price = na

// RIGHT — persists across bars
var float entry_price = na
```
This is the most common bug. Your variable looks like it's tracking state but it resets every bar.

### 2. Repainting from Missing `barstate.isconfirmed`
```pine
// WRONG — fires on incomplete bars, then disappears
if longCondition
    strategy.entry("Long", strategy.long)

// RIGHT — only fires on confirmed bars
if longCondition and barstate.isconfirmed
    strategy.entry("Long", strategy.long)
```

### 3. Future Data Leak with `lookahead_on`
```pine
// WRONG — peeks at future bar's close
htf = request.security(syminfo.tickerid, "D", close, barmerge.gaps_off, barmerge.lookahead_on)

// RIGHT — uses current bar's data only
htf = request.security(syminfo.tickerid, "D", close, barmerge.gaps_off, barmerge.lookahead_off)
```

### 4. Mismatched Entry/Exit IDs
```pine
// WRONG — exit never triggers because IDs don't match
strategy.entry("Long Entry", strategy.long)
strategy.exit("Exit", from_entry="Long", stop=sl)

// RIGHT — IDs match exactly
strategy.entry("Long", strategy.long)
strategy.exit("Exit Long", from_entry="Long", stop=sl)
```

### 5. Using Bare `security()` Instead of `request.security()`
```pine
// WRONG — deprecated, may not compile
data = security("BINANCE:BTCUSDT", "60", close)

// RIGHT — v6 namespace
data = request.security(syminfo.tickerid, "60", close, barmerge.gaps_off, barmerge.lookahead_off)
```

### 6. `calc_on_every_tick=true` in Backtests
This recalculates the strategy on every tick during live execution but not during backtesting. Result: backtest shows one thing, live trading behaves differently. Always use `false`.

### 7. No `na` Checks on Derived Values
```pine
// WRONG — will error if ta.pivothigh returns na
float level = ta.pivothigh(high, 5, 5)
if close > level  // Error: cannot compare with na

// RIGHT — guard against na
float level = ta.pivothigh(high, 5, 5)
if not na(level) and close > level
    // safe
```

### 8. Variable Shadowing Pine Built-ins
```pine
// WRONG — shadows the built-in 'volume' variable
volume = custom_volume_calc()  // Now 'volume' no longer means candle volume

// RIGHT — use a descriptive name
custom_vol = custom_volume_calc()
```

---

## Strategy Template Scaffold (10-Step Structure)

Every well-structured Pine Script strategy follows this order:

```pine
// ============================================================
// STEP 1: Version & Declaration
// ============================================================
//@version=6
strategy("Strategy Name", overlay=true, initial_capital=10000,
         default_qty_type=strategy.percent_of_equity, default_qty_value=100,
         commission_type=strategy.commission.percent, commission_value=0.06,
         slippage=2, calc_on_every_tick=false)

// ============================================================
// STEP 2: Inputs
// ============================================================
swing_len = input.int(5, "Swing Length", minval=1, maxval=20)
atr_len = input.int(14, "ATR Length")
atr_sl_mult = input.float(1.5, "ATR SL Multiplier", step=0.1)
atr_tp_mult = input.float(3.0, "ATR TP Multiplier", step=0.1)
min_score = input.int(4, "Min Confluence Score", minval=1, maxval=8)

// ============================================================
// STEP 3: Calculations (indicators, ATR, EMAs, etc.)
// ============================================================
atr_val = ta.atr(atr_len)
ema_fast = ta.ema(close, 20)
ema_slow = ta.ema(close, 50)

// ============================================================
// STEP 4: Market Structure (swing points, trend detection)
// ============================================================
ph = ta.pivothigh(high, swing_len, swing_len)
pl = ta.pivotlow(low, swing_len, swing_len)
// ... swing tracking with var variables

// ============================================================
// STEP 5: SMC Pattern Detection (CHoCH, BOS, OB, FVG)
// ============================================================
// ... pattern detection logic

// ============================================================
// STEP 6: Multi-Timeframe Data (if needed)
// ============================================================
// htf_data = request.security(syminfo.tickerid, "60", close,
//                              barmerge.gaps_off, barmerge.lookahead_off)

// ============================================================
// STEP 7: Confluence Scoring (optional)
// ============================================================
// score = 0
// if condition1: score += weight1
// ...

// ============================================================
// STEP 8: Entry & Exit Conditions
// ============================================================
long_condition = false  // ... your logic
short_condition = false // ... your logic

if long_condition and barstate.isconfirmed
    strategy.entry("Long", strategy.long)
    strategy.exit("Exit Long", from_entry="Long",
                  stop=close - atr_val * atr_sl_mult,
                  limit=close + atr_val * atr_tp_mult)

if short_condition and barstate.isconfirmed
    strategy.entry("Short", strategy.short)
    strategy.exit("Exit Short", from_entry="Short",
                  stop=close + atr_val * atr_sl_mult,
                  limit=close - atr_val * atr_tp_mult)

// ============================================================
// STEP 9: Plotting & Visualization
// ============================================================
plot(ema_fast, "EMA 20", color=color.blue)
plot(ema_slow, "EMA 50", color=color.red)
// plotshape, bgcolor, label.new, box.new, etc.

// ============================================================
// STEP 10: Alerts
// ============================================================
alertcondition(long_condition and barstate.isconfirmed,
               title="Long Entry", message="LONG {{ticker}} @ {{close}}")
alertcondition(short_condition and barstate.isconfirmed,
               title="Short Entry", message="SHORT {{ticker}} @ {{close}}")
```

---

## Usage Examples

### Generate a strategy
```bash
python pinescript_ai.py generate "15m SMC reversal with CHoCH + Order Block in discount zone, ATR stops"
python pinescript_ai.py generate "BTC scalper using RSI divergence with volume confirmation" --output my_strategy.pine
python pinescript_ai.py generate "Multi-timeframe trend follower" --model claude-sonnet-4-20250514
```

### Validate a file
```bash
python pinescript_ai.py validate examples/smc_reversal.pine
```

### Explain a strategy
```bash
python pinescript_ai.py explain examples/confluence_scorer.pine
```

### View templates
```bash
python pinescript_ai.py templates
```

### Get backtest analysis
```bash
python pinescript_ai.py backtest-summary examples/smc_reversal.pine
```
