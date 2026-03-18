#!/usr/bin/env python3
"""Pine Script v6 Generator — Production-grade CLI for generating, validating,
and analyzing TradingView Pine Script strategies with deep Smart Money Concepts knowledge."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

app = typer.Typer(
    name="pinescript-ai",
    help="Generate, validate, and analyze Pine Script v6 strategies.",
    add_completion=False,
)
console = Console()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "claude-sonnet-4-20250514"

PINE_BUILTINS = {
    "open", "high", "low", "close", "volume", "time", "bar_index",
    "na", "true", "false", "color", "math", "ta", "str", "array",
    "matrix", "map", "strategy", "input", "plot", "hline", "fill",
    "label", "line", "box", "table", "request", "ticker", "syminfo",
    "timeframe", "barstate", "chart",
}

DEPRECATED_FUNCTIONS: dict[str, str] = {
    "security(": "request.security(",
    "study(": "indicator(",
    "tickerid": "syminfo.tickerid",
    "transp=": "color.new() with transparency parameter",
    "color.rgb(": "Ensure using color.rgb() correctly — check parameters",
    "nz(": "nz( is valid but verify usage — often misused with series",
    "input(": "Use typed inputs: input.int(), input.float(), input.bool(), input.string(), input.source()",
}

# ---------------------------------------------------------------------------
# System prompt — 2000+ words of genuine Pine Script v6 + SMC trading knowledge
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an expert Pine Script v6 developer and quantitative trader specializing in Smart Money Concepts (SMC) and institutional order flow strategies. You generate production-ready, compilable Pine Script v6 code for TradingView.

## CRITICAL PINE SCRIPT v6 RULES

### Version & Declaration
- ALWAYS start with `//@version=6`
- Use `strategy()` for backtestable strategies, `indicator()` for studies
- NEVER use `study()` — it was removed in v5+
- Strategy defaults MUST be realistic for crypto:
  ```
  strategy("Name", overlay=true, initial_capital=10000,
           default_qty_type=strategy.percent_of_equity, default_qty_value=100,
           commission_type=strategy.commission.percent, commission_value=0.06,
           slippage=2, calc_on_every_tick=false, process_orders_on_close=false)
  ```
- `commission_value=0.06` reflects Bybit/Binance taker fees (0.06%)
- `slippage=2` accounts for 2 ticks of slippage — realistic for liquid crypto pairs
- `calc_on_every_tick=false` prevents intra-bar recalculation that causes false signals
- `process_orders_on_close=false` prevents lookahead bias from processing at bar close

### Namespaces & Functions
- ALL indicator functions use `ta.*` namespace: `ta.sma()`, `ta.ema()`, `ta.rsi()`, `ta.atr()`, `ta.crossover()`, `ta.crossunder()`, `ta.highest()`, `ta.lowest()`, `ta.change()`, `ta.valuewhen()`, `ta.barssince()`
- ALL math functions use `math.*`: `math.abs()`, `math.max()`, `math.min()`, `math.round()`, `math.log()`, `math.sqrt()`
- ALL string functions use `str.*`: `str.tostring()`, `str.format()`
- Multi-timeframe data uses `request.security()` — NEVER use bare `security()`
- ALWAYS use `barmerge.lookahead_off` in `request.security()` to prevent future data leaking:
  ```
  htf_close = request.security(syminfo.tickerid, "60", close, barmerge.gaps_off, barmerge.lookahead_off)
  ```
- Use `syminfo.tickerid` — NEVER bare `tickerid`
- Use `timeframe.period` for current timeframe string

### Variable Declaration & State
- Use `var` keyword for variables that persist across bars and only initialize once:
  ```
  var float entry_price = na
  var int trade_direction = 0
  var bool choch_detected = false
  ```
- Without `var`, variables reinitialize every bar — this is the #1 source of bugs
- Use `varip` only for variables that update on every tick (rare, usually for real-time-only indicators)
- Pine Script has NO objects or classes — use parallel arrays or multiple variables
- Arrays: `array.new_float()`, `array.push()`, `array.get()`, `array.size()`

### Anti-Repainting Rules (CRITICAL)
- ALWAYS guard strategy entries with `barstate.isconfirmed`:
  ```
  if barstate.isconfirmed and longCondition
      strategy.entry("Long", strategy.long)
  ```
- This ensures signals only fire on confirmed (closed) bars, preventing repainting
- `barstate.isconfirmed` is true on the last tick of a bar — the bar is fully formed
- Without this guard, signals can appear and disappear as the current bar forms
- For `request.security()`, ALWAYS use `barmerge.lookahead_off` — using `lookahead_on` peeks into future data
- NEVER reference `close` on the current bar for entry decisions without `barstate.isconfirmed`
- Historical bars always have `barstate.isconfirmed = true`, so backtests remain accurate

### Strategy Orders
- Entry: `strategy.entry("Long", strategy.long)` or `strategy.entry("Short", strategy.short)`
- Exit: `strategy.exit("Exit Long", from_entry="Long", stop=sl, limit=tp)`
- The `from_entry` parameter in `strategy.exit()` MUST match the `id` in `strategy.entry()`
- `strategy.close("Long")` closes by ID — use for conditional exits
- `strategy.cancel_all()` cancels pending orders
- Position sizing: use `qty` parameter or set defaults in `strategy()` declaration
- For pyramiding (multiple entries), set `pyramiding=N` in strategy declaration

### Alerts & Webhooks
- Use `alertcondition()` for TradingView alert dialog conditions:
  ```
  alertcondition(longCondition and barstate.isconfirmed, title="Long Entry", message="LONG {{ticker}} @ {{close}}")
  ```
- Use `alert()` for programmatic alerts (webhooks, automation):
  ```
  if longCondition and barstate.isconfirmed
      alert("LONG " + syminfo.ticker + " @ " + str.tostring(close), alert.freq_once_per_bar_close)
  ```
- `alert.freq_once_per_bar_close` prevents duplicate alerts
- For webhook JSON payloads:
  ```
  alert('{"action":"buy","ticker":"' + syminfo.ticker + '","price":' + str.tostring(close) + '}', alert.freq_once_per_bar_close)
  ```

### Plotting & Visual Output
- `plot()` for line plots, `plotshape()` for markers, `plotchar()` for character markers
- `bgcolor()` for background coloring zones
- `label.new()` for dynamic text labels on chart
- `line.new()` for drawing trend lines, support/resistance
- `box.new()` for highlighting zones (order blocks, FVG areas)
- Colors: `color.new(color.red, 80)` for transparency (0=opaque, 100=invisible)
- Use `display.none` parameter to hide plots from chart but keep for alerts

## SMART MONEY CONCEPTS (SMC) — INSTITUTIONAL TRADING PATTERNS

### Market Structure: Swing Points
Swing highs and lows form the backbone of all SMC analysis. A swing high has a lower high on both sides; a swing low has a higher low on both sides.
```
// Swing detection with lookback
swingLen = input.int(5, "Swing Length")
isSwingHigh = ta.pivothigh(high, swingLen, swingLen)
isSwingLow = ta.pivotlow(low, swingLen, swingLen)
```
Note: `ta.pivothigh()` and `ta.pivotlow()` return `na` when no pivot is found, and they have a built-in offset of `swingLen` bars — the pivot is confirmed `swingLen` bars after it actually occurred.

### Change of Character (CHoCH)
CHoCH is a break AGAINST the prevailing trend — the first signal of potential reversal.
- In an uptrend (series of higher highs, higher lows): CHoCH = price breaks below the most recent swing low
- In a downtrend (lower highs, lower lows): CHoCH = price breaks above the most recent swing high
- CHoCH is a WARNING, not an entry signal by itself — it needs confirmation (order block, FVG, etc.)
- Implementation: track the most recent swing high/low, detect when price closes beyond it against the trend direction

### Break of Structure (BOS)
BOS is a break WITH the prevailing trend — confirmation that the trend continues.
- In an uptrend: BOS = price breaks above the most recent swing high (new higher high)
- In a downtrend: BOS = price breaks below the most recent swing low (new lower low)
- BOS confirms the trend is intact and is used for continuation trades
- After a CHoCH, the first BOS in the new direction confirms the reversal

### Order Blocks (OB)
An Order Block is the last opposing candle before an impulsive move — it represents where institutions placed large orders.
- Bullish OB: the last bearish (red) candle before a strong bullish impulse that creates a BOS
- Bearish OB: the last bullish (green) candle before a strong bearish impulse that creates a BOS
- To find an OB, walk BACK from the BOS candle using a `for` loop:
  ```
  // Find bullish order block — last bearish candle before bullish impulse
  var float ob_top = na
  var float ob_bottom = na
  if bullish_bos
      for i = 1 to 20
          if close[i] < open[i]  // bearish candle
              ob_top := high[i]
              ob_bottom := low[i]
              break
  ```
- Price returning to an OB is a high-probability entry zone
- OBs in premium/discount zones are higher quality
- An OB is "mitigated" (invalidated) when price trades through it completely

### Fair Value Gaps (FVG)
An FVG is a 3-candle imbalance where price moved so fast it left a gap — areas price tends to return to fill.
- Bullish FVG: `low[0] > high[2]` — gap between candle 0's low and candle 2's high (price moved up fast)
- Bearish FVG: `high[0] < low[2]` — gap between candle 0's high and candle 2's low (price moved down fast)
- The FVG zone is between `high[2]` and `low[0]` for bullish, `low[2]` and `high[0]` for bearish
- FVGs act as magnets — price tends to return and fill them before continuing
- Unfilled FVGs in the direction of the trend are high-quality entry zones
```
bullish_fvg = low > high[2]
fvg_top = low
fvg_bottom = high[2]
```

### Liquidity Sweeps
Liquidity pools form at equal highs/lows where stop losses cluster. Smart money sweeps these levels to fill large orders before reversing.
- Equal highs detection: multiple swing highs within a small threshold (e.g., 0.1% of price)
- Equal lows detection: multiple swing lows within a small threshold
- A sweep occurs when price exceeds the liquidity level but closes back below/above it:
  ```
  // Bearish liquidity sweep (sweep of equal highs)
  swept_high = high > liquidity_level and close < liquidity_level
  ```
- Sweeps followed by CHoCH are high-probability reversal setups
- The sweep "fills" institutional orders sitting above/below the obvious level

### Premium & Discount Zones
- Calculate the range: `range_high = ta.highest(high, lookback)`, `range_low = ta.lowest(low, lookback)`
- Equilibrium (50%): `eq = (range_high + range_low) / 2`
- Premium zone: above equilibrium — look for shorts
- Discount zone: below equilibrium — look for longs
- OBs and FVGs in the correct zone (discount for longs, premium for shorts) are higher probability

### Confluence Scoring Pattern
The best SMC setups combine multiple factors. Use a point-based system:
```
var int score = 0
score := 0  // reset each bar
if in_discount_zone
    score += 1
if bullish_ob_present
    score += 2
if bullish_fvg_present
    score += 1
if choch_detected
    score += 2
if volume_above_average
    score += 1
if htf_trend_bullish
    score += 1

// Require minimum score for entry
min_score = input.int(4, "Min Confluence Score")
long_entry = score >= min_score and barstate.isconfirmed
```

## RISK MANAGEMENT TEMPLATES

### ATR-Based Stop Loss & Take Profit
```
atr_val = ta.atr(14)
atr_mult_sl = input.float(1.5, "ATR SL Multiplier")
atr_mult_tp = input.float(3.0, "ATR TP Multiplier")
long_sl = close - atr_val * atr_mult_sl
long_tp = close + atr_val * atr_mult_tp
```

### Structural Stop Loss
Place stops beyond the structure that defines the trade:
- Long entry at OB: stop below the OB low
- Short entry at OB: stop above the OB high
- Always add a small buffer (e.g., `ob_low - atr_val * 0.2`)

### Position Sizing by Risk Percent
```
risk_percent = input.float(1.0, "Risk %") / 100
risk_amount = strategy.equity * risk_percent
position_size = risk_amount / math.abs(close - stop_loss)
```

## OUTPUT RULES
1. Output ONLY the Pine Script code — no markdown fences, no explanations before/after
2. Code must be immediately compilable in TradingView without edits
3. Include clear comments explaining each section
4. Use `input.*()` for all tunable parameters so users can adjust in TradingView UI
5. Include both `alertcondition()` and `alert()` for maximum compatibility
6. Test edge cases: what happens on bar 0? What if na values propagate? Always use `na` checks where needed
7. Every `strategy.entry()` must have a matching `strategy.exit()` with proper `from_entry`
8. Include `barstate.isconfirmed` on all entry conditions"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_client() -> "anthropic.Anthropic":
    """Create and return an Anthropic client, checking for API key."""
    try:
        import anthropic
    except ImportError:
        console.print("[red]Error:[/red] anthropic package not installed. Run: pip install anthropic")
        raise typer.Exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[red]Error:[/red] ANTHROPIC_API_KEY environment variable not set.")
        raise typer.Exit(1)

    return anthropic.Anthropic(api_key=api_key)


def _call_claude(prompt: str, system: str, model: str) -> str:
    """Send a prompt to Claude and return the text response.

    Args:
        prompt: The user message to send.
        system: The system prompt providing context.
        model: The Anthropic model ID to use.

    Returns:
        The text content of Claude's response.
    """
    client = _get_client()
    message = client.messages.create(
        model=model,
        max_tokens=16000,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _read_pine_file(path: str) -> str:
    """Read a Pine Script file and return its contents.

    Args:
        path: Path to the .pine file.

    Returns:
        The file contents as a string.

    Raises:
        typer.Exit: If the file doesn't exist or can't be read.
    """
    file_path = Path(path)
    if not file_path.exists():
        console.print(f"[red]Error:[/red] File not found: {path}")
        raise typer.Exit(1)
    if not file_path.suffix == ".pine":
        console.print(f"[yellow]Warning:[/yellow] File does not have .pine extension: {path}")
    return file_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Command: generate
# ---------------------------------------------------------------------------


@app.command()
def generate(
    description: str = typer.Argument(..., help="Natural language description of the strategy to generate"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Save output to a .pine file"),
    model: str = typer.Option(DEFAULT_MODEL, "--model", "-m", help="Anthropic model ID"),
    no_validate: bool = typer.Option(False, "--no-validate", help="Skip post-generation validation"),
) -> None:
    """Generate a compilable Pine Script v6 strategy from a natural language description.

    Uses Claude with deep Pine Script v6 and Smart Money Concepts knowledge to
    produce production-ready TradingView strategies.
    """
    console.print(Panel(f"[bold cyan]Generating Pine Script v6 strategy[/bold cyan]\n{description}", title="Pine Script AI"))

    with console.status("[bold green]Calling Claude API..."):
        code = _call_claude(description, SYSTEM_PROMPT, model)

    # Strip markdown fences if Claude wraps the output
    code = _strip_markdown_fences(code)

    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(code, encoding="utf-8")
        console.print(f"\n[green]Saved to:[/green] {out_path}")

    if not no_validate and output:
        console.print("\n[bold]Running validation...[/bold]")
        issues = _validate_pine(code)
        if issues:
            _print_validation_table(issues)
        else:
            console.print("[green]No issues found.[/green]")

    if not output:
        console.print(Panel(code, title="Generated Pine Script v6", border_style="green"))


def _strip_markdown_fences(code: str) -> str:
    """Remove markdown code fences from Claude's output if present.

    Args:
        code: Raw text that may contain ```pine or ``` wrappers.

    Returns:
        Clean Pine Script code without markdown artifacts.
    """
    # Remove opening fence with optional language tag
    code = re.sub(r"^```(?:pine|pinescript)?\s*\n", "", code, count=1)
    # Remove closing fence
    code = re.sub(r"\n```\s*$", "", code, count=1)
    return code.strip()


# ---------------------------------------------------------------------------
# Command: validate
# ---------------------------------------------------------------------------


@app.command()
def validate(
    path: str = typer.Argument(..., help="Path to a .pine file to validate"),
) -> None:
    """Run comprehensive validation checks on a Pine Script file.

    Checks for deprecated functions, repainting risks, bracket balance,
    entry/exit pairing, and other common mistakes.
    """
    code = _read_pine_file(path)
    issues = _validate_pine(code)

    if issues:
        console.print(Panel(f"[bold]Validation Results:[/bold] {path}", title="Pine Script Validator"))
        _print_validation_table(issues)
        error_count = sum(1 for i in issues if i[0] == "error")
        warn_count = sum(1 for i in issues if i[0] == "warning")
        info_count = sum(1 for i in issues if i[0] == "info")
        console.print(f"\n[red]{error_count} errors[/red]  [yellow]{warn_count} warnings[/yellow]  [blue]{info_count} info[/blue]")
    else:
        console.print(Panel("[bold green]All checks passed![/bold green]", title="Pine Script Validator"))


def _validate_pine(code: str) -> list[tuple[str, int, str]]:
    """Run all validation checks on Pine Script code.

    Args:
        code: The Pine Script source code to validate.

    Returns:
        A list of (severity, line_number, message) tuples.
        Severity is one of: 'error', 'warning', 'info'.
    """
    issues: list[tuple[str, int, str]] = []
    lines = code.split("\n")

    # 1. Version declaration
    _check_version(lines, issues)

    # 2. Deprecated functions
    _check_deprecated(lines, issues)

    # 3. Lookahead check
    _check_lookahead(lines, issues)

    # 4. Bracket / parenthesis balance
    _check_brackets(lines, issues)

    # 5. Entry/exit pairing
    _check_entry_exit_pairing(lines, issues)

    # 6. barstate.isconfirmed presence
    _check_barstate_confirmed(lines, issues)

    # 7. alertcondition presence in strategies
    _check_alertcondition(lines, issues)

    # 8. Bare tickerid usage
    _check_tickerid(lines, issues)

    # 9. Variable shadowing of built-ins
    _check_variable_shadowing(lines, issues)

    # 10. calc_on_every_tick check
    _check_calc_on_every_tick(lines, issues)

    return issues


def _check_version(lines: list[str], issues: list[tuple[str, int, str]]) -> None:
    """Check for proper //@version=6 declaration.

    Args:
        lines: Source code lines.
        issues: List to append findings to.
    """
    has_version = False
    for i, line in enumerate(lines):
        if re.match(r"^\s*//@version=", line):
            has_version = True
            if "//@version=6" not in line:
                issues.append(("error", i + 1, f"Expected //@version=6, found: {line.strip()}"))
            break
    if not has_version:
        issues.append(("error", 0, "Missing //@version=6 declaration"))


def _check_deprecated(lines: list[str], issues: list[tuple[str, int, str]]) -> None:
    """Check for deprecated Pine Script functions.

    Args:
        lines: Source code lines.
        issues: List to append findings to.
    """
    # Only check for clearly deprecated patterns
    deprecated_checks = {
        "security(": ("error", "Deprecated: use request.security() instead of security()"),
        "study(": ("error", "Deprecated: use indicator() instead of study()"),
    }
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("//"):
            continue
        for pattern, (severity, msg) in deprecated_checks.items():
            # Avoid matching request.security(
            if pattern == "security(" and "request.security(" in stripped:
                continue
            if pattern in stripped:
                issues.append((severity, i + 1, msg))


def _check_lookahead(lines: list[str], issues: list[tuple[str, int, str]]) -> None:
    """Check for lookahead_on usage which causes future data leakage.

    Handles multi-line request.security() calls by scanning forward until
    the matching closing parenthesis.

    Args:
        lines: Source code lines.
        issues: List to append findings to.
    """
    for i, line in enumerate(lines):
        if "lookahead_on" in line and not line.strip().startswith("//"):
            issues.append(("error", i + 1, "barmerge.lookahead_on detected — causes future data leakage. Use barmerge.lookahead_off"))
        if "request.security(" in line and not line.strip().startswith("//"):
            # Gather the full call across continuation lines
            full_call = line
            paren_depth = line.count("(") - line.count(")")
            j = i + 1
            while paren_depth > 0 and j < len(lines):
                full_call += " " + lines[j]
                paren_depth += lines[j].count("(") - lines[j].count(")")
                j += 1
            if "lookahead" not in full_call:
                issues.append(("warning", i + 1, "request.security() without explicit lookahead parameter — add barmerge.lookahead_off"))


def _check_brackets(lines: list[str], issues: list[tuple[str, int, str]]) -> None:
    """Check bracket and parenthesis balance across the entire file.

    Args:
        lines: Source code lines.
        issues: List to append findings to.
    """
    counts = {"(": 0, "[": 0}
    closers = {")": "(", "]": "["}
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("//"):
            continue
        in_string = False
        string_char = None
        for ch in stripped:
            if ch in ('"', "'") and not in_string:
                in_string = True
                string_char = ch
            elif ch == string_char and in_string:
                in_string = False
                string_char = None
            elif not in_string:
                if ch in counts:
                    counts[ch] += 1
                elif ch in closers:
                    opener = closers[ch]
                    counts[opener] -= 1

    if counts["("] != 0:
        issues.append(("error", 0, f"Unbalanced parentheses: {'unclosed' if counts['('] > 0 else 'extra closing'} ({abs(counts['('])})"))
    if counts["["] != 0:
        issues.append(("error", 0, f"Unbalanced brackets: {'unclosed' if counts['['] > 0 else 'extra closing'} ({abs(counts['['])})"))


def _check_entry_exit_pairing(lines: list[str], issues: list[tuple[str, int, str]]) -> None:
    """Check that strategy.exit() from_entry IDs match strategy.entry() IDs.

    Args:
        lines: Source code lines.
        issues: List to append findings to.
    """
    entry_ids: set[str] = set()
    exit_from_ids: set[str] = set()

    entry_pattern = re.compile(r'strategy\.entry\(\s*["\']([^"\']+)["\']')
    exit_pattern = re.compile(r'from_entry\s*=\s*["\']([^"\']+)["\']')

    for line in lines:
        if line.strip().startswith("//"):
            continue
        for m in entry_pattern.finditer(line):
            entry_ids.add(m.group(1))
        for m in exit_pattern.finditer(line):
            exit_from_ids.add(m.group(1))

    # Check exits reference valid entries
    for exit_id in exit_from_ids:
        if exit_id not in entry_ids:
            issues.append(("error", 0, f'strategy.exit() references from_entry="{exit_id}" but no matching strategy.entry("{exit_id}") found'))

    # Check entries have exits
    for entry_id in entry_ids:
        if entry_id not in exit_from_ids:
            issues.append(("warning", 0, f'strategy.entry("{entry_id}") has no matching strategy.exit() with from_entry="{entry_id}"'))


def _check_barstate_confirmed(lines: list[str], issues: list[tuple[str, int, str]]) -> None:
    """Check that strategies with entries use barstate.isconfirmed.

    Args:
        lines: Source code lines.
        issues: List to append findings to.
    """
    has_entry = any("strategy.entry(" in line for line in lines if not line.strip().startswith("//"))
    has_confirmed = any("barstate.isconfirmed" in line for line in lines if not line.strip().startswith("//"))

    if has_entry and not has_confirmed:
        issues.append(("warning", 0, "Strategy has entries but no barstate.isconfirmed check — risk of repainting signals"))


def _check_alertcondition(lines: list[str], issues: list[tuple[str, int, str]]) -> None:
    """Check that strategies include alertcondition() for TradingView alerts.

    Args:
        lines: Source code lines.
        issues: List to append findings to.
    """
    has_strategy = any("strategy(" in line for line in lines if not line.strip().startswith("//"))
    has_alert = any(
        ("alertcondition(" in line or "alert(" in line)
        for line in lines
        if not line.strip().startswith("//")
    )

    if has_strategy and not has_alert:
        issues.append(("info", 0, "Strategy has no alertcondition() or alert() — consider adding for webhook/notification support"))


def _check_tickerid(lines: list[str], issues: list[tuple[str, int, str]]) -> None:
    """Check for bare tickerid usage instead of syminfo.tickerid.

    Args:
        lines: Source code lines.
        issues: List to append findings to.
    """
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("//"):
            continue
        # Match bare tickerid not preceded by syminfo. or a word char
        if re.search(r'(?<!\w)(?<!syminfo\.)tickerid(?!\w)', stripped):
            issues.append(("warning", i + 1, "Bare 'tickerid' found — use syminfo.tickerid instead"))


def _check_variable_shadowing(lines: list[str], issues: list[tuple[str, int, str]]) -> None:
    """Check for variable names that shadow Pine Script built-ins.

    Args:
        lines: Source code lines.
        issues: List to append findings to.
    """
    # Match simple variable assignments: identifier = value (not ==)
    assign_pattern = re.compile(r"^(?:var\s+(?:float|int|bool|string|color)\s+)?(\w+)\s*=[^=]")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("//"):
            continue
        m = assign_pattern.match(stripped)
        if m:
            var_name = m.group(1)
            if var_name in PINE_BUILTINS and var_name not in ("na", "true", "false", "color"):
                issues.append(("warning", i + 1, f"Variable '{var_name}' shadows a Pine Script built-in"))


def _check_calc_on_every_tick(lines: list[str], issues: list[tuple[str, int, str]]) -> None:
    """Check for calc_on_every_tick=true which can cause unrealistic backtests.

    Args:
        lines: Source code lines.
        issues: List to append findings to.
    """
    for i, line in enumerate(lines):
        if "calc_on_every_tick" in line and "true" in line and not line.strip().startswith("//"):
            issues.append(("warning", i + 1, "calc_on_every_tick=true can cause unrealistic backtests — signals may fire on incomplete bars"))


def _print_validation_table(issues: list[tuple[str, int, str]]) -> None:
    """Print validation issues as a Rich table.

    Args:
        issues: List of (severity, line_number, message) tuples.
    """
    table = Table(title="Validation Issues", show_lines=True)
    table.add_column("Severity", style="bold", width=10)
    table.add_column("Line", justify="right", width=6)
    table.add_column("Issue", ratio=1)

    severity_styles = {
        "error": "[red]ERROR[/red]",
        "warning": "[yellow]WARN[/yellow]",
        "info": "[blue]INFO[/blue]",
    }

    for severity, line_num, message in sorted(issues, key=lambda x: ({"error": 0, "warning": 1, "info": 2}[x[0]], x[1])):
        line_str = str(line_num) if line_num > 0 else "—"
        table.add_row(severity_styles.get(severity, severity), line_str, message)

    console.print(table)


# ---------------------------------------------------------------------------
# Command: explain
# ---------------------------------------------------------------------------

EXPLAIN_SYSTEM = """You are a Pine Script v6 expert analyst. Given a Pine Script strategy or indicator, provide a structured analysis in this EXACT format:

## What It Does
2-3 sentences describing the overall purpose and approach.

## Entry Conditions
- Bullet point for each long entry condition
- Bullet point for each short entry condition

## Exit Conditions
- Bullet point for each exit mechanism (stop loss, take profit, trailing, conditional)

## Risk Management
Describe the risk management approach: position sizing, stop loss method, take profit method, max drawdown protection.

## Recommended Usage
- **Timeframe:** The ideal timeframe(s) for this strategy
- **Market:** What market conditions and pairs suit this strategy
- **Session:** Any preferred trading sessions

## Key Parameters to Tune
| Parameter | Current Value | Suggested Range | Impact |
|-----------|--------------|-----------------|--------|
| param_name | value | min-max | What it affects |

Keep analysis concrete and actionable. Reference specific line numbers when relevant."""


@app.command()
def explain(
    path: str = typer.Argument(..., help="Path to a .pine file to analyze"),
    model: str = typer.Option(DEFAULT_MODEL, "--model", "-m", help="Anthropic model ID"),
) -> None:
    """Send a Pine Script file to Claude for structured analysis.

    Returns what the strategy does, entry/exit conditions, risk management
    approach, recommended timeframe, and key parameters to tune.
    """
    code = _read_pine_file(path)

    console.print(Panel(f"[bold cyan]Analyzing:[/bold cyan] {path}", title="Pine Script Explainer"))

    with console.status("[bold green]Analyzing strategy with Claude..."):
        analysis = _call_claude(
            f"Analyze this Pine Script strategy:\n\n{code}",
            EXPLAIN_SYSTEM,
            model,
        )

    console.print(Panel(analysis, title="Strategy Analysis", border_style="cyan", padding=(1, 2)))


# ---------------------------------------------------------------------------
# Command: templates
# ---------------------------------------------------------------------------

TEMPLATES = [
    {
        "name": "SMC Reversal (CHoCH + OB in Discount)",
        "description": "Detects Change of Character against the trend, then enters at the Order Block in the discount zone. Best for ranging-to-trending transitions on 15m-1H.",
        "prompt": "Generate a Pine Script v6 strategy: Detect bearish-to-bullish CHoCH (price breaks above the most recent lower high), then find the bullish Order Block (last bearish candle before the CHoCH impulse) using a for loop walking back up to 20 bars. Only enter long if price returns to the OB zone AND we're in the discount zone (below 50% of the recent range). Use ATR(14) * 1.5 for stop loss below the OB low, take profit at 2.5R. Add alertcondition for entries. Use 15-minute timeframe defaults.",
    },
    {
        "name": "SMC Continuation (BOS + FVG Entry)",
        "description": "Identifies Break of Structure with the trend, waits for price to fill a Fair Value Gap before entering. Trend-following with precise entries on 5m-15m.",
        "prompt": "Generate a Pine Script v6 strategy: Detect bullish BOS (price breaks above the most recent swing high creating a new higher high). After BOS, identify any bullish Fair Value Gap (low > high[2]) left behind during the impulse. Enter long when price retraces into the FVG zone. Stop loss below the FVG bottom minus ATR(14) * 0.5 buffer. Take profit at the BOS high plus 1x the risk distance. Track trend direction using swing highs/lows with a lookback of 5 bars. Include both long and short setups.",
    },
    {
        "name": "Liquidity Sweep Reversal",
        "description": "Detects equal highs/lows (liquidity pools), waits for a sweep followed by CHoCH and OB confirmation. The classic 'stop hunt reversal' setup on 15m-4H.",
        "prompt": "Generate a Pine Script v6 strategy: Detect equal highs and equal lows using a threshold of 0.1% of price. When price sweeps above equal highs (high exceeds the level but close is back below), mark as a bearish liquidity sweep. Then require a bearish CHoCH within 10 bars of the sweep. Find the bearish Order Block (last bullish candle before the CHoCH impulse). Enter short when price returns to the OB zone. Stop loss above the sweep high plus ATR(14) * 0.3. Take profit at 3R. Mirror logic for bullish sweeps of equal lows. Use var for all persistent state.",
    },
    {
        "name": "Multi-Timeframe Confluence (1H Bias + 15m Entry)",
        "description": "Uses 1H timeframe for trend bias via market structure, enters on 15m using OB/FVG setups aligned with the higher timeframe direction.",
        "prompt": "Generate a Pine Script v6 strategy: Use request.security() with barmerge.lookahead_off to get 1H swing structure (trend direction based on higher highs/lows vs lower highs/lows). On the 15m chart, only take long entries when 1H trend is bullish, and short entries when 1H trend is bearish. Entry trigger on 15m: CHoCH in the direction of the 1H bias, followed by price entering an Order Block. Stop loss below/above the OB. Take profit at the next 1H structure level. Position size at 1% risk of equity. Include a trend strength filter using 1H ADX above 20.",
    },
    {
        "name": "EMA Volume Breakout",
        "description": "Classic momentum strategy: EMA 20/50 crossover confirmed by 1.5x average volume surge. Simple but effective for trending crypto on 1H-4H.",
        "prompt": "Generate a Pine Script v6 strategy: Enter long when EMA(20) crosses above EMA(50) AND current volume is at least 1.5x the 20-period SMA of volume. Enter short on the opposite crossover with volume confirmation. Use ATR(14) * 2 for stop loss, ATR(14) * 3 for take profit. Add a trend filter: only take longs above EMA(200), shorts below. Include position sizing at 2% risk per trade. Plot EMAs on chart, highlight volume bars that meet the threshold. Add alerts for both entries.",
    },
    {
        "name": "Funding Rate Scalper (RSI Extreme + Structure)",
        "description": "Designed for crypto: enters on RSI extremes when price is at a structural level (support/resistance). Catches mean reversion at key levels on 5m-15m.",
        "prompt": "Generate a Pine Script v6 strategy: Enter long when RSI(14) drops below 30 AND price is at or near a swing low support level (within ATR(14) * 0.5 of the most recent swing low). Enter short when RSI(14) rises above 70 AND price is near a swing high resistance. Use the swing low/high as the stop loss level with a small ATR buffer. Take profit at the EMA(20) — mean reversion target. Add a filter: skip entries if ADX(14) > 40 (too trendy for mean reversion). Max 1 trade at a time (pyramiding=0). Include 0.06% commission for crypto exchanges.",
    },
    {
        "name": "Confluence Scorer (Point System, Enter at Score >= 4)",
        "description": "Awards points for multiple SMC and technical factors. Only enters when confluence score meets the minimum threshold. Highly customizable framework.",
        "prompt": "Generate a Pine Script v6 strategy: Build a confluence scoring system for long entries. Award points: +2 for bullish CHoCH detected within last 10 bars, +2 for price in a bullish Order Block zone, +1 for bullish Fair Value Gap present, +1 for price in discount zone (below 50% of 50-bar range), +1 for volume above 20-period average, +1 for 1H trend bullish (via request.security with lookahead_off). Display the current score on the chart using a label. Enter long when score >= 4 (configurable via input) and barstate.isconfirmed. Mirror for short entries with bearish equivalents. Use ATR-based stops at 1.5x below entry, TP at 2R. Plot score as a histogram in a separate pane.",
    },
]


@app.command()
def templates() -> None:
    """Display 7 preset strategy prompts for common trading setups.

    Shows SMC and technical analysis templates with names, descriptions,
    and the exact prompts to use with the generate command.
    """
    console.print(Panel("[bold cyan]Pine Script v6 Strategy Templates[/bold cyan]\nCopy any prompt below and use it with: [green]python pinescript_ai.py generate \"<prompt>\"[/green]", title="Templates"))

    for idx, t in enumerate(TEMPLATES, 1):
        prompt_text = Text(t["prompt"], style="dim")
        panel_content = f"[bold]{t['description']}[/bold]\n\n[yellow]Prompt:[/yellow]\n{t['prompt']}"
        console.print(Panel(
            panel_content,
            title=f"[bold white]{idx}. {t['name']}[/bold white]",
            border_style="cyan",
            padding=(1, 2),
        ))
        console.print()


# ---------------------------------------------------------------------------
# Command: backtest-summary
# ---------------------------------------------------------------------------

BACKTEST_SYSTEM = """You are a quantitative trading analyst specializing in strategy evaluation. Given a Pine Script strategy, analyze its logic and provide a theoretical assessment. You have NOT run a backtest — you are analyzing the CODE LOGIC to estimate behavior.

Respond in this EXACT format:

## Strategy Overview
1-2 sentences on what this strategy does.

## Estimated Win Rate Range
Provide a realistic percentage range (e.g., 35-45%) based on the entry logic quality, with reasoning.

## Estimated Profit Factor
Provide a range (e.g., 1.2-1.8) based on the risk:reward ratio and win rate estimate.

## Ideal Market Conditions
- Bullet points describing when this strategy should perform well
- Be specific: trending vs ranging, volatility level, session times

## Weaknesses & Failure Modes
- Bullet points on when this strategy will lose money
- Common failure scenarios based on the logic
- Be honest and specific

## Parameter Optimization Suggestions
| Parameter | Current | Suggested Range | Why |
|-----------|---------|-----------------|-----|
| name | value | range | reasoning |

## Overall Assessment
2-3 sentences: is this strategy worth live testing? What needs improvement?

Be realistic and honest. Do not inflate expectations. Most strategies have a 40-55% win rate and profit factors of 1.1-1.5 in live conditions. Account for slippage, fees, and execution delays."""


@app.command(name="backtest-summary")
def backtest_summary(
    path: str = typer.Argument(..., help="Path to a .pine file to analyze"),
    model: str = typer.Option(DEFAULT_MODEL, "--model", "-m", help="Anthropic model ID"),
) -> None:
    """Analyze a Pine Script strategy and estimate its theoretical performance.

    Sends the strategy to Claude for analysis of expected win rate, profit factor,
    ideal market conditions, weaknesses, and optimization suggestions.
    """
    code = _read_pine_file(path)

    console.print(Panel(f"[bold cyan]Analyzing backtest characteristics:[/bold cyan] {path}", title="Backtest Summary"))

    with console.status("[bold green]Analyzing strategy logic with Claude..."):
        analysis = _call_claude(
            f"Analyze this Pine Script strategy's theoretical performance characteristics:\n\n{code}",
            BACKTEST_SYSTEM,
            model,
        )

    console.print(Panel(analysis, title="Theoretical Backtest Analysis", border_style="magenta", padding=(1, 2)))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
