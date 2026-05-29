# CasinoScript Language Specification

**Version 1.0 · May 2026**  
*A domain-specific scripting language for defining, simulating, and backtesting roulette betting strategies.*

---

## Table of Contents

1. [Overview](#1-overview)
2. [File Format](#2-file-format)
3. [Session Configuration](#3-session-configuration)
4. [Steps and Labels](#4-steps-and-labels)
5. [Bet Placement](#5-bet-placement)
   - 5.1 [Bet Types Reference](#51-bet-types-reference)
6. [The SPIN Statement](#6-the-spin-statement)
7. [Conditional Branching](#7-conditional-branching)
   - 7.1 [Outcome Conditions](#71-outcome-conditions)
   - 7.2 [Streak Conditions](#72-streak-conditions)
   - 7.3 [Bankroll Conditions](#73-bankroll-conditions)
   - 7.4 [Spin History Conditions](#74-spin-history-conditions)
8. [Bet Modifiers](#8-bet-modifiers)
9. [Flow Control](#9-flow-control)
10. [Logging and Output](#10-logging-and-output)
11. [Comments](#11-comments)
12. [Execution Model](#12-execution-model)
13. [Error Handling](#13-error-handling)
14. [Complete Examples](#14-complete-examples)
15. [Reserved Keywords](#15-reserved-keywords)
16. [Changelog](#16-changelog)

---

## 1. Overview

CasinoScript is a plain-text scripting language for encoding roulette betting strategies. A script describes a sequence of **steps**, each containing one or more **bets**, a **spin**, and **conditional branches** that direct flow based on the result.

Scripts are consumed by the CasinoScript Backtest Engine, which replays them against either randomly generated spins (Monte Carlo) or a recorded spin history (CSV replay), then produces a detailed performance report.

**Design principles:**

- Human-readable — a strategy card from a casino forum should translate into CasinoScript with minimal effort
- Unambiguous — every keyword has exactly one meaning
- Portable — plain `.cs` text files, no binary formats
- Wheel-accurate — all American roulette rules apply (0, 00, house edge ~5.26%)

---

## 2. File Format

| Property | Value |
|---|---|
| Extension | `.cs` |
| Encoding | UTF-8 |
| Line endings | LF or CRLF (both accepted) |
| Case sensitivity | Keywords are **case-insensitive**; labels are case-sensitive |
| Whitespace | Leading/trailing whitespace on each line is ignored |
| Blank lines | Ignored |

A valid CasinoScript file contains:

1. An optional **configuration block** (before the first `STEP`)
2. One or more **STEP blocks**

---

## 3. Session Configuration

Configuration statements appear at the top of the file, before any `STEP` declaration. All are optional unless noted.

```
BANKROLL <amount>
```
Sets the starting bankroll in dollars. **Required.**  
Example: `BANKROLL 500`

---

```
STOP LOSS <amount>
```
Halt the session if the bankroll falls to or below this value.  
Example: `STOP LOSS 100`

---

```
STOP WIN <amount>
```
Halt the session if the bankroll rises to or above this value.  
Example: `STOP WIN 1000`

---

```
MAX SPINS <n>
```
Halt the session after `n` total spins regardless of outcome.  
Example: `MAX SPINS 200`

---

```
MAX LOSSES <n>
```
Halt the session after `n` consecutive losses.  
Example: `MAX LOSSES 5`

---

```
MAX WINS <n>
```
Halt the session after `n` consecutive wins.  
Example: `MAX WINS 10`

---

```
SPIN SOURCE RANDOM
SPIN SOURCE FILE "<path>"
```
Define where spin data comes from.  
- `RANDOM` — Monte Carlo; spins are generated internally (default)
- `FILE "<path>"` — replay spins from a CSV file (one pocket per line: `7`, `00`, `14`, …)

Example: `SPIN SOURCE FILE "recorded_spins.csv"`

---

```
CURRENCY <symbol>
```
Symbol used in log output. Default: `$`.  
Example: `CURRENCY $`

---

### Full Configuration Example

```
BANKROLL 500
STOP LOSS 200
STOP WIN 800
MAX SPINS 150
SPIN SOURCE RANDOM
CURRENCY $
```

---

## 4. Steps and Labels

A **STEP** is a named block of instructions. Steps are the primary unit of flow control.

```
STEP <identifier>
```

- `<identifier>` may be a positive integer (`1`, `2`, `3`) or a descriptive name (`RESET`, `MARTINGALE`, `RECOVERY`)
- Step names must be unique within a script
- Execution begins at the **first STEP** defined in the file
- Steps do not fall through — execution within a step ends at the first `IF WIN` / `IF LOSS` branch or an explicit `GOTO`

```
STEP 1
  BET 10 ON DOZEN 1
  BET 10 ON DOZEN 2
  SPIN
  IF WIN GOTO STEP 1
  IF LOSS GOTO STEP 2

STEP 2
  BET 30 ON DOZEN 1
  BET 30 ON DOZEN 2
  SPIN
  IF WIN GOTO STEP 1
  IF LOSS GOTO STEP 2
```

> **Convention:** Use integer step names for simple linear strategies and descriptive names for complex multi-branch strategies.

---

## 5. Bet Placement

```
BET <amount> ON <bet_type> [<qualifier>]
```

- `<amount>` — a positive number in dollars; decimals allowed (`2.50`)
- `<bet_type>` — one of the types in §5.1
- `<qualifier>` — required for some bet types; see table below

Multiple `BET` statements within a step are placed simultaneously on the same spin.

**Examples:**

```
BET 10 ON DOZEN 1
BET 5  ON RED
BET 15 ON STRAIGHT 17
BET 10 ON STREET 4
BET 5  ON SPLIT 8
BET 20 ON COLUMN 2
BET 10 ON EVEN
BET 10 ON LOW
```

### 5.1 Bet Types Reference

| Keyword | Qualifier | Payout | Description |
|---|---|---|---|
| `STRAIGHT` | `<number>` 0–36 or `00` | 35:1 | Single pocket |
| `SPLIT` | `<lowest_number>` | 17:1 | Two adjacent pockets; engine infers partner (vertical preferred) |
| `STREET` | `<row>` 1–12 | 11:1 | Three-number row |
| `CORNER` | `<top_left>` | 8:1 | Four-number square; engine infers all four from top-left |
| `LINE` | `<start_row>` 1–11 | 5:1 | Six numbers across two adjacent rows |
| `FIVE` | *(none)* | 6:1 | 0, 00, 1, 2, 3 — American wheel only |
| `DOZEN` | `1`, `2`, or `3` | 2:1 | 1–12, 13–24, or 25–36 |
| `COLUMN` | `1`, `2`, or `3` | 2:1 | Vertical column of 12 numbers |
| `RED` | *(none)* | 1:1 | All red pockets |
| `BLACK` | *(none)* | 1:1 | All black pockets |
| `EVEN` | *(none)* | 1:1 | All even numbers |
| `ODD` | *(none)* | 1:1 | All odd numbers |
| `LOW` | *(none)* | 1:1 | 1–18 |
| `HIGH` | *(none)* | 1:1 | 19–36 |

> **Note:** `0` and `00` are neither odd/even, low/high, red/black. They lose all outside bets.

---

## 6. The SPIN Statement

```
SPIN
```

Executes one spin of the wheel. The engine:

1. Draws the next pocket (random or from file)
2. Evaluates all `BET` statements placed in the current step
3. Calculates net result for the spin
4. Updates the running bankroll
5. Records the result in the spin log
6. Evaluates the `IF WIN` / `IF LOSS` branches that follow

Each `STEP` must contain exactly **one** `SPIN` statement. The `SPIN` must appear **after** all `BET` statements and **before** any `IF` branches.

```
STEP 1
  BET 10 ON RED        # ✅ BET before SPIN
  SPIN                 # ✅ SPIN in the middle
  IF WIN GOTO STEP 1   # ✅ IF after SPIN
  IF LOSS GOTO STEP 2
```

---

## 7. Conditional Branching

All conditional statements must appear **after** `SPIN` within a step. They are evaluated in order; the first matching condition is executed and remaining conditions in the step are skipped.

### 7.1 Outcome Conditions

```
IF WIN  <action>
IF LOSS <action>
IF PUSH <action>
```

`WIN` — the spin produced a net positive result (at least one bet hit).  
`LOSS` — the spin produced a net negative result (no bets hit).  
`PUSH` — reserved for future rule variants; treated as `LOSS` on a standard American wheel.

**Actions:**

| Action | Meaning |
|---|---|
| `GOTO STEP <identifier>` | Jump to the named step |
| `REPEAT` | Re-execute the current step with the same bets |
| `STOP` | End the session immediately and report |

```
IF WIN  GOTO STEP 1
IF LOSS GOTO STEP 2
IF WIN  REPEAT
IF LOSS STOP
```

---

### 7.2 Streak Conditions

```
IF STREAK WIN  > <n> <action>
IF STREAK WIN  = <n> <action>
IF STREAK LOSS > <n> <action>
IF STREAK LOSS = <n> <action>
```

Branches based on the current consecutive win or loss streak.

```
IF STREAK LOSS > 3 GOTO STEP RESET
IF STREAK WIN  = 5 STOP
```

---

### 7.3 Bankroll Conditions

```
IF BANKROLL <  <amount> <action>
IF BANKROLL >  <amount> <action>
IF BANKROLL <= <amount> <action>
IF BANKROLL >= <amount> <action>
IF BANKROLL =  <amount> <action>
```

```
IF BANKROLL < 50  STOP
IF BANKROLL > 900 GOTO STEP LOCK_PROFIT
```

---

### 7.4 Spin History Conditions

Branch based on what the wheel has recently produced.

```
IF LAST IS <pocket>          # last spin landed on this pocket/color/parity
IF LAST IS NOT <pocket>
IF LAST_N <n> ALL <color>    # last n spins were all this color
IF LAST_N <n> NO  <color>    # none of the last n spins were this color
```

`<pocket>` may be a number (`0`–`36`, `00`), a color (`RED`, `BLACK`, `GREEN`), or a parity (`EVEN`, `ODD`).

```
IF LAST IS RED       GOTO STEP RED_FOLLOW
IF LAST IS NOT BLACK GOTO STEP HEDGE
IF LAST_N 5 ALL RED  GOTO STEP BLACK_CHASE
IF LAST_N 3 NO GREEN GOTO STEP CONTINUE
```

---

## 8. Bet Modifiers

Bet modifiers adjust wager amounts. They appear **inside a STEP, before SPIN**.

---

```
DOUBLE BETS
```
Double all wagers placed in the current step.

---

```
RESET BETS
```
Reset all wagers to the amounts defined in `STEP 1` (the base step).

---

```
INCREASE BET BY <amount>
INCREASE BET BY <multiplier>X
```
Increase all current wagers by a flat dollar amount or a multiplier.

```
INCREASE BET BY 10       # add $10 to each bet
INCREASE BET BY 2X       # multiply each bet by 2 (same as DOUBLE BETS)
INCREASE BET BY 1.5X     # multiply by 1.5
```

---

```
DECREASE BET BY <amount>
DECREASE BET BY <multiplier>X
```
Decrease all current wagers. A bet cannot go below `$0.01`; the engine clips at the minimum.

---

```
SET BET <amount> ON <bet_type> [<qualifier>]
```
Override the amount for a specific bet type within the current step.

```
SET BET 50 ON DOZEN 1
SET BET 50 ON DOZEN 2
```

---

## 9. Flow Control

```
GOTO STEP <identifier>
```
Unconditional jump to the named step. Valid inside or outside a conditional.

---

```
REPEAT
```
Re-run the current step from its first `BET` statement. Equivalent to `GOTO STEP <current>`.

---

```
STOP
```
Terminate the session immediately. The engine generates the final report.

---

## 10. Logging and Output

```
NOTE "<text>"
```
Writes a free-text annotation to the spin log at the point of execution.  
Example: `NOTE "Entering recovery phase"`

---

```
PRINT BANKROLL
```
Writes the current bankroll value to the spin log.

---

```
PRINT BETS
```
Writes the current bet layout (type, amount) to the spin log.

---

```
PRINT STATS
```
Writes a running statistics snapshot (spins, wins, losses, net P&L) to the log.

---

## 11. Comments

Any text following a `#` character on a line is treated as a comment and ignored by the engine.

```
# This is a full-line comment
BET 10 ON DOZEN 1   # This is an inline comment
```

Block comments are not supported. Use multiple `#` lines for multi-line comments.

---

## 12. Execution Model

The engine follows these rules on every spin cycle:

1. **Enter step** — load all `BET` statements
2. **Check bankroll** — if total wager exceeds bankroll, apply `STOP LOSS` behavior
3. **Execute SPIN** — draw pocket, evaluate bets, update bankroll
4. **Evaluate conditions** — in order from top to bottom; first match wins
5. **Check session limits** — `STOP LOSS`, `STOP WIN`, `MAX SPINS`, `MAX LOSSES`, `MAX WINS`
6. **Jump** — follow the winning branch to the next step

**Infinite loop protection:** If a script cycles through the same step more than 10,000 times without a `STOP` or session-limit trigger, the engine halts and reports a warning.

**Bankroll exhaustion:** If a bet would exceed the remaining bankroll, the engine scales all bets proportionally to fit. If the bankroll is below `$0.01`, the session ends with a `BUST` result.

---

## 13. Error Handling

The engine validates the script before execution and reports all errors with line numbers.

| Error | Example |
|---|---|
| Unknown keyword | `WAGER 10 ON RED` |
| Invalid bet type | `BET 10 ON CORNER RED` |
| Missing qualifier | `BET 10 ON DOZEN` |
| Amount out of range | `BET 0 ON RED` or `BET -5 ON BLACK` |
| Duplicate step name | Two `STEP 1` declarations |
| Undefined GOTO target | `GOTO STEP 99` with no `STEP 99` defined |
| SPIN missing from step | A step with `BET` and `IF` but no `SPIN` |
| BET after SPIN | `SPIN` appears before all `BET` statements |
| IF before SPIN | `IF WIN` appears before `SPIN` in the step |
| Unreachable step | A step that no `GOTO` or fall-through ever reaches |

Warnings (non-fatal):

| Warning | Meaning |
|---|---|
| No `STOP LOSS` defined | Session may run until bankroll is zero |
| No `MAX SPINS` defined | Session may run indefinitely |
| Unreachable step | Defined but never jumped to |

---

## 14. Complete Examples

### 14.1 City of Gold

```
# ─────────────────────────────────────────────
# City of Gold Strategy
# Bets on 1st and 2nd dozens; doubles on loss
# ─────────────────────────────────────────────

BANKROLL 500
STOP LOSS 200
MAX SPINS 100

STEP 1
  NOTE "Base bet — $10 on Dozen 1 and Dozen 2"
  BET 10 ON DOZEN 1
  BET 10 ON DOZEN 2
  SPIN
  IF WIN  GOTO STEP 1
  IF LOSS GOTO STEP 2

STEP 2
  NOTE "Recovery — $30 on Dozen 1 and Dozen 2"
  BET 30 ON DOZEN 1
  BET 30 ON DOZEN 2
  SPIN
  IF WIN  GOTO STEP 1
  IF LOSS GOTO STEP 2
```

---

### 14.2 Martingale on Red

```
# ─────────────────────────────────────────────
# Classic Martingale — Red only
# Double bet after every loss, reset on win
# ─────────────────────────────────────────────

BANKROLL 500
STOP LOSS 0
MAX SPINS 200

STEP 1
  BET 5 ON RED
  SPIN
  IF WIN  REPEAT
  IF LOSS GOTO STEP 2

STEP 2
  BET 10 ON RED
  SPIN
  IF WIN  GOTO STEP 1
  IF LOSS GOTO STEP 3

STEP 3
  BET 20 ON RED
  SPIN
  IF WIN  GOTO STEP 1
  IF LOSS GOTO STEP 4

STEP 4
  BET 40 ON RED
  SPIN
  IF WIN  GOTO STEP 1
  IF LOSS GOTO STEP 5

STEP 5
  BET 80 ON RED
  SPIN
  IF WIN  GOTO STEP 1
  IF LOSS STOP
```

---

### 14.3 D'Alembert with Streak Guard

```
# ─────────────────────────────────────────────
# D'Alembert — Even/Odd
# Increase by $5 on loss, decrease by $5 on win
# Bail out after 6 consecutive losses
# ─────────────────────────────────────────────

BANKROLL 300
STOP LOSS 100
MAX SPINS 150

STEP BASE
  BET 10 ON EVEN
  SPIN
  IF STREAK LOSS > 5  GOTO STEP BAIL
  IF WIN              GOTO STEP WIN_STEP
  IF LOSS             GOTO STEP LOSS_STEP

STEP WIN_STEP
  DECREASE BET BY 5
  BET 5 ON EVEN
  SPIN
  IF WIN  GOTO STEP WIN_STEP
  IF LOSS GOTO STEP LOSS_STEP

STEP LOSS_STEP
  INCREASE BET BY 5
  BET 15 ON EVEN
  SPIN
  IF STREAK LOSS > 5  GOTO STEP BAIL
  IF WIN              GOTO STEP WIN_STEP
  IF LOSS             GOTO STEP LOSS_STEP

STEP BAIL
  NOTE "Bail triggered — 6 consecutive losses"
  PRINT STATS
  STOP
```

---

### 14.4 History-Aware Black Chase

```
# ─────────────────────────────────────────────
# Black Chase
# Wait for 4 consecutive reds, then bet black
# ─────────────────────────────────────────────

BANKROLL 400
STOP LOSS 150
MAX SPINS 300

STEP WATCH
  NOTE "Observing — waiting for 4 reds in a row"
  SPIN
  IF LAST_N 4 ALL RED  GOTO STEP CHASE
  IF WIN               REPEAT
  IF LOSS              REPEAT

STEP CHASE
  NOTE "4 reds seen — chasing black"
  BET 25 ON BLACK
  SPIN
  IF WIN  GOTO STEP WATCH
  IF LOSS GOTO STEP DOUBLE_CHASE

STEP DOUBLE_CHASE
  BET 50 ON BLACK
  SPIN
  IF WIN  GOTO STEP WATCH
  IF LOSS GOTO STEP WATCH
```

---

## 15. Reserved Keywords

The following words are reserved and may not be used as step names or identifiers.

| Category | Keywords |
|---|---|
| Configuration | `BANKROLL`, `STOP`, `MAX`, `SPIN`, `SOURCE`, `RANDOM`, `FILE`, `CURRENCY` |
| Steps | `STEP`, `GOTO`, `REPEAT` |
| Betting | `BET`, `ON`, `SET`, `DOUBLE`, `INCREASE`, `DECREASE`, `RESET`, `BETS`, `BY` |
| Bet types | `STRAIGHT`, `SPLIT`, `STREET`, `CORNER`, `LINE`, `FIVE`, `DOZEN`, `COLUMN`, `RED`, `BLACK`, `EVEN`, `ODD`, `LOW`, `HIGH` |
| Conditions | `IF`, `WIN`, `LOSS`, `PUSH`, `STREAK`, `LAST`, `LAST_N`, `ALL`, `NO`, `IS`, `NOT`, `BANKROLL` |
| Comparators | `<`, `>`, `<=`, `>=`, `=` |
| Output | `NOTE`, `PRINT`, `STATS` |
| Terminators | `STOP`, `BUST` |

---

## 16. Changelog

| Version | Date | Notes |
|---|---|---|
| 1.0 | May 2026 | Initial specification |

---

*CasinoScript is designed to work with the Python-based CasinoScript Backtest Engine. For engine usage, see `ENGINE.md`.*