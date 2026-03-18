# Pine Script Generator — Project Instructions

## Stack
- Python 3.11+
- Typer for CLI
- Rich for terminal output formatting
- Anthropic SDK for Claude API access

## Code Standards
- PEP 8 style
- Type hints on all function signatures
- Docstrings on all public functions
- No `# type: ignore` unless absolutely necessary

## CLI Entry Point
- `pinescript_ai.py` — single-file Typer CLI
- Run with: `python pinescript_ai.py <command>`

## Environment
- `ANTHROPIC_API_KEY` must be set for generate/explain/backtest-summary commands
- Validation and templates work offline

## Testing
- `python pinescript_ai.py validate examples/smc_reversal.pine`
- `python pinescript_ai.py templates`

## Key Conventions
- Pine Script output must always target v6
- All generated strategies must include `barstate.isconfirmed` guards
- All `request.security()` calls must use `barmerge.lookahead_off`
- System prompts live inline in pinescript_ai.py — they encode real trading knowledge, not filler
