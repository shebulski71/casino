"""
American Roulette — Terminal Edition
Full bet types, bankroll tracking, session statistics, and CSV import.
Powered by the Rich library for professional terminal output.

CSV FORMAT  (type_code, number, amount)
─────────────────────────────────────────────────────────────────
Type  Description              Number column
 1    Straight up (35:1)       Exact pocket: 0-36 or 00
 2    Split       (17:1)       Lowest of the two adjacent numbers
 3    Street      (11:1)       Row number 1-12
 4    Corner       (8:1)       Top-left number of the 2×2 square
 5    Line         (5:1)       Starting row 1-11
 6    Five Number  (6:1)       Any value (ignored)
 7    Dozen        (2:1)       1, 2, or 3
 8    Column       (2:1)       1, 2, or 3
 9    Red/Black    (1:1)       1=Red, 2=Black
10    Even/Odd     (1:1)       1=Even, 2=Odd
11    Low/High     (1:1)       1=Low(1-18), 2=High(19-36)

Example — three street bets on rows 1,2,3 at $5 each:
  3,1,5
  3,2,5
  3,3,5
─────────────────────────────────────────────────────────────────
"""

import csv
import os
import random
import time
from dataclasses import dataclass, field
from typing import Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.style import Style
from rich.align import Align
from rich.live import Live
from rich.spinner import Spinner

console = Console()

# ─────────────────────────────────────────────
#  Wheel layout
# ─────────────────────────────────────────────

RED_NUMBERS  = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
BLACK_NUMBERS = {2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35}
WHEEL = list(range(0, 37)) + ["00"]

ROWS    = [[3*r-2, 3*r-1, 3*r] for r in range(1, 13)]
COLUMNS = [[c + 3*r for r in range(0, 12)] for c in [1, 2, 3]]
DOZENS  = [list(range(1, 13)), list(range(13, 25)), list(range(25, 37))]

def pocket_color(n) -> str:
    if n in RED_NUMBERS:   return "red"
    if n in BLACK_NUMBERS: return "white"
    return "green"

def pocket_label(n) -> str:
    col = pocket_color(n)
    return f"[bold {col}]{str(n):>2}[/]"

# ─────────────────────────────────────────────
#  Bet definitions
# ─────────────────────────────────────────────

@dataclass
class Bet:
    name:    str
    numbers: list
    payout:  int

def straight_bet(n)          -> Bet: return Bet(f"Straight {n}",            [n],                          35)
def split_bet(a, b)          -> Bet: return Bet(f"Split {a}/{b}",           [a, b],                       17)
def street_bet(row: int)     -> Bet:
    nums = ROWS[row - 1]
    return Bet(f"Street {nums[0]}-{nums[2]}", nums, 11)
def corner_bet(a,b,c,d)      -> Bet: return Bet(f"Corner {a}/{b}/{c}/{d}",  [a, b, c, d],                  8)
def line_bet(row: int)       -> Bet:
    nums = ROWS[row - 1] + ROWS[row]
    return Bet(f"Line {nums[0]}-{nums[5]}", nums, 5)
def dozen_bet(d: int)        -> Bet: return Bet(f"Dozen {d}",               DOZENS[d-1],                   2)
def column_bet(c: int)       -> Bet: return Bet(f"Column {c}",              COLUMNS[c-1],                  2)
def even_money_bet(name, nums) -> Bet: return Bet(name, nums, 1)

FIVE_NUMBER = Bet("Five Number (0,00,1,2,3)", [0, "00", 1, 2, 3], 6)

# ─────────────────────────────────────────────
#  Session stats
# ─────────────────────────────────────────────

@dataclass
class Stats:
    spins:             int   = 0
    wins:              int   = 0
    losses:            int   = 0
    total_wagered:     float = 0.0
    total_won:         float = 0.0
    biggest_win:       float = 0.0
    biggest_loss:      float = 0.0
    starting_bankroll: float = 0.0
    history:           list  = field(default_factory=list)

    def record(self, spin: int, result, net: float, wagered: float):
        self.spins         += 1
        self.total_wagered += wagered
        if net > 0:
            self.wins      += 1
            self.total_won += net
            self.biggest_win = max(self.biggest_win, net)
        elif net < 0:
            self.losses    += 1
            self.biggest_loss = min(self.biggest_loss, net)
        self.history.append((spin, result, net))

    def summary(self, bankroll: float):
        net      = bankroll - self.starting_bankroll
        win_rate = (self.wins / self.spins * 100) if self.spins else 0
        edge     = ((self.total_won - self.total_wagered) / self.total_wagered * 100
                    if self.total_wagered else 0)

        t = Table(
            title="[bold gold1]📊  SESSION STATISTICS[/]",
            box=box.DOUBLE_EDGE,
            border_style="gold1",
            show_header=False,
            min_width=44,
        )
        t.add_column("Metric", style="bold cyan",  no_wrap=True)
        t.add_column("Value",  style="bold white", justify="right")

        net_style  = "bold green" if net >= 0 else "bold red"
        edge_style = "bold green" if edge >= 0 else "bold red"

        t.add_row("Spins played",    str(self.spins))
        t.add_row("Wins",            f"[green]{self.wins}[/]")
        t.add_row("Losses",          f"[red]{self.losses}[/]")
        t.add_row("Win rate",        f"{win_rate:.1f}%")
        t.add_row("Total wagered",   f"${self.total_wagered:,.2f}")
        t.add_row("Net result",      f"[{net_style}]{'+' if net>=0 else ''}${net:,.2f}[/]")
        t.add_row("Biggest win",     f"[green]+${self.biggest_win:,.2f}[/]")
        t.add_row("Biggest loss",    f"[red]${self.biggest_loss:,.2f}[/]")
        t.add_row("Player edge",     f"[{edge_style}]{edge:.2f}%[/]  [dim](house ~5.26%)[/]")
        t.add_row("Final bankroll",  f"[bold yellow]${bankroll:,.2f}[/]")

        console.print()
        console.print(Align.center(t))

# ─────────────────────────────────────────────
#  Spin history  (observation + live spins)
# ─────────────────────────────────────────────

@dataclass
class SpinRecord:
    number:  object   # int 0-36 or str "00"
    color:   str      # "Red" | "Black" | "Green"
    wagered: bool     # False = observation spin, True = live bet spin
    net:     float    # 0.0 for observation spins


class SpinHistory:
    def __init__(self):
        self.records: list[SpinRecord] = []

    def add(self, number, wagered: bool, net: float = 0.0):
        col = pocket_color(number) if isinstance(number, int) else "green"
        color_name = "Red" if col == "red" else ("Black" if col == "white" else "Green")
        self.records.append(SpinRecord(number, color_name, wagered, net))

    def print_table(self, last_n: int = 20):
        if not self.records:
            console.print("  [dim]No spins recorded yet.[/]")
            return

        shown = self.records[-last_n:]

        t = Table(
            title=f"[bold cyan]Spin History[/]  [dim](last {len(shown)} of {len(self.records)})[/]",
            box=box.SIMPLE_HEAVY,
            border_style="cyan",
            show_lines=False,
            min_width=52,
        )
        t.add_column("#",      style="dim",      justify="right",  width=4)
        t.add_column("Result", justify="center", width=8)
        t.add_column("Color",  justify="center", width=8)
        t.add_column("Type",   justify="center", width=12)
        t.add_column("Net",    justify="right",  width=12)

        for i, r in enumerate(shown, start=len(self.records) - len(shown) + 1):
            rich_col = "red" if r.color == "Red" else ("bright_white" if r.color == "Black" else "green")
            num_str  = f"[bold {rich_col}]{str(r.number):>2}[/]"
            col_str  = f"[bold {rich_col}]{r.color}[/]"

            if r.wagered:
                type_str = "[dim]live[/]"
                net_str  = (f"[green]+${r.net:,.2f}[/]" if r.net >= 0
                            else f"[red]-${abs(r.net):,.2f}[/]")
            else:
                type_str = "[yellow]observe[/]"
                net_str  = "[dim]—[/]"

            t.add_row(str(i), num_str, col_str, type_str, net_str)

        # Quick frequency footer
        reds   = sum(1 for r in self.records if r.color == "Red")
        blacks = sum(1 for r in self.records if r.color == "Black")
        greens = sum(1 for r in self.records if r.color == "Green")
        obs    = sum(1 for r in self.records if not r.wagered)
        live   = sum(1 for r in self.records if r.wagered)

        t.add_section()
        t.add_row(
            "",
            f"[red]R:{reds}[/]  [bright_white]B:{blacks}[/]  [green]G:{greens}[/]",
            "", f"[dim]obs:{obs}  live:{live}[/]", "",
        )

        console.print()
        console.print(Align.center(t))

    def last_numbers(self, n: int = 10) -> list:
        """Return the last n pocket numbers across all spin types."""
        return [r.number for r in self.records[-n:]]


# ─────────────────────────────────────────────
#  Rich UI helpers
# ─────────────────────────────────────────────

def title_banner():
    banner = Text(justify="center")
    banner.append("\n")
    banner.append("  ██████╗  ██████╗ ██╗   ██╗██╗     ███████╗████████╗████████╗███████╗\n", style="bold red")
    banner.append("  ██╔══██╗██╔═══██╗██║   ██║██║     ██╔════╝╚══██╔══╝╚══██╔══╝██╔════╝\n", style="bold red")
    banner.append("  ██████╔╝██║   ██║██║   ██║██║     █████╗     ██║      ██║   █████╗  \n", style="bold red")
    banner.append("  ██╔══██╗██║   ██║██║   ██║██║     ██╔══╝     ██║      ██║   ██╔══╝  \n", style="bold red")
    banner.append("  ██║  ██║╚██████╔╝╚██████╔╝███████╗███████╗   ██║      ██║   ███████╗\n", style="bold red")
    banner.append("  ╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚══════╝╚══════╝   ╚═╝      ╚═╝   ╚══════╝\n", style="bold red")
    banner.append("\n  American Casino Roulette  ·  00 Wheel  ·  Full Bets  ·  Double Down  ·  CSV Import\n", style="dim white")
    console.print(Panel(banner, border_style="red", box=box.DOUBLE_EDGE))

def spin_animation(result):
    label = pocket_label(result)
    col   = pocket_color(result) if isinstance(result, int) else "green"
    color_name = "Red" if col == "red" else ("Black" if col == "white" else "Green")

    frames = ["◐","◓","◑","◒"]
    end_time = time.time() + 2.8
    i = 0
    while time.time() < end_time:
        console.print(f"\r  {frames[i % 4]}  [bold]Spinning the wheel...[/]", end="")
        time.sleep(0.07)
        i += 1
    console.print(
        f"\r  [bold yellow]✦[/]  Ball lands on: "
        f"[bold {col}] {str(result):>2} [/]  "
        f"[dim]({color_name})[/]          "
    )

def print_bankroll_header(bankroll: float, spin_num: int, history=None):
    recent = ""
    if history and history.records:
        nums  = history.last_numbers(8)
        parts = []
        for n in nums:
            col = pocket_color(n) if isinstance(n, int) else "green"
            rc  = "red" if col == "red" else ("bright_white" if col == "white" else "green")
            parts.append(f"[{rc}]{str(n):>2}[/]")
        recent = "  [dim]Recent:[/] " + " ".join(parts)
    console.print(Rule(
        f"[bold cyan]💰 Bankroll: [yellow]${bankroll:,.2f}[/]   [dim]Spin #{spin_num}[/]{recent}",
        style="dim"
    ))

def prompt_float(msg: str, lo: float, hi: float) -> float:
    while True:
        try:
            v = float(console.input(f"  [cyan]{msg}[/] "))
            if lo <= v <= hi:
                return v
            console.print(f"  [red]Enter a value between {lo} and {hi}.[/]")
        except ValueError:
            console.print("  [red]Please enter a number.[/]")

def prompt_int(msg: str, lo: int, hi: int) -> int:
    while True:
        try:
            v = int(console.input(f"  [cyan]{msg}[/] "))
            if lo <= v <= hi:
                return v
            console.print(f"  [red]Enter a value between {lo} and {hi}.[/]")
        except ValueError:
            console.print("  [red]Please enter a whole number.[/]")

def prompt_number_on_board(msg: str):
    while True:
        raw = console.input(f"  [cyan]{msg}[/] ").strip()
        if raw == "00":
            return "00"
        try:
            n = int(raw)
            if 0 <= n <= 36:
                return n
        except ValueError:
            pass
        console.print("  [red]Enter 0–36 or 00.[/]")

def are_adjacent_split(a, b) -> bool:
    if not (isinstance(a, int) and isinstance(b, int) and a >= 1 and b >= 1):
        return False
    for row in ROWS:
        if a in row and b in row:
            if abs(row.index(a) - row.index(b)) == 1:
                return True
    return abs(a - b) == 3

# ─────────────────────────────────────────────
#  CSV import
# ─────────────────────────────────────────────

class CSVImportError(Exception):
    pass

def bet_from_row(type_code: int, number: str, amount: float) -> Bet:
    t, n = type_code, number.strip()

    if t == 1:
        if n == "00": return straight_bet("00")
        v = int(n) if n.lstrip("-").isdigit() else (_ for _ in ()).throw(CSVImportError(f"Straight: need 0-36 or 00, got '{n}'"))
        if not (0 <= v <= 36): raise CSVImportError(f"Straight: out of range: {v}")
        return straight_bet(v)

    elif t == 2:
        if not n.lstrip("-").isdigit(): raise CSVImportError(f"Split: need integer, got '{n}'")
        lo = int(n)
        if not (1 <= lo <= 35): raise CSVImportError(f"Split: lowest must be 1-35, got {lo}")
        hi = lo + 3 if lo + 3 <= 36 else lo + 1
        if not are_adjacent_split(lo, hi): raise CSVImportError(f"Split: can't infer partner for {lo}")
        return split_bet(lo, hi)

    elif t == 3:
        if not n.lstrip("-").isdigit(): raise CSVImportError(f"Street: need row 1-12, got '{n}'")
        row = int(n)
        if not (1 <= row <= 12): raise CSVImportError(f"Street: row out of range: {row}")
        return street_bet(row)

    elif t == 4:
        if not n.lstrip("-").isdigit(): raise CSVImportError(f"Corner: need integer, got '{n}'")
        tl = int(n)
        col_pos = ((tl - 1) % 3) + 1
        row_num  = (tl - 1) // 3 + 1
        if col_pos == 3: raise CSVImportError(f"Corner: top-left {tl} is in col 3; use col 1 or 2")
        if row_num > 11: raise CSVImportError(f"Corner: top-left {tl} is in row 12; no row below")
        return corner_bet(tl, tl+1, tl+3, tl+4)

    elif t == 5:
        if not n.lstrip("-").isdigit(): raise CSVImportError(f"Line: need row 1-11, got '{n}'")
        row = int(n)
        if not (1 <= row <= 11): raise CSVImportError(f"Line: row out of range: {row}")
        return line_bet(row)

    elif t == 6:
        return FIVE_NUMBER

    elif t == 7:
        if not n.lstrip("-").isdigit(): raise CSVImportError(f"Dozen: need 1-3, got '{n}'")
        d = int(n)
        if d not in (1,2,3): raise CSVImportError(f"Dozen: need 1-3, got {d}")
        return dozen_bet(d)

    elif t == 8:
        if not n.lstrip("-").isdigit(): raise CSVImportError(f"Column: need 1-3, got '{n}'")
        c = int(n)
        if c not in (1,2,3): raise CSVImportError(f"Column: need 1-3, got {c}")
        return column_bet(c)

    elif t == 9:
        if not n.lstrip("-").isdigit(): raise CSVImportError(f"Red/Black: 1=Red 2=Black, got '{n}'")
        v = int(n)
        if v == 1: return even_money_bet("Red",   list(RED_NUMBERS))
        if v == 2: return even_money_bet("Black", list(BLACK_NUMBERS))
        raise CSVImportError(f"Red/Black: 1=Red 2=Black, got {v}")

    elif t == 10:
        if not n.lstrip("-").isdigit(): raise CSVImportError(f"Even/Odd: 1=Even 2=Odd, got '{n}'")
        v = int(n)
        if v == 1: return even_money_bet("Even", [x for x in range(2, 37, 2)])
        if v == 2: return even_money_bet("Odd",  [x for x in range(1, 37, 2)])
        raise CSVImportError(f"Even/Odd: 1=Even 2=Odd, got {v}")

    elif t == 11:
        if not n.lstrip("-").isdigit(): raise CSVImportError(f"Low/High: 1=Low 2=High, got '{n}'")
        v = int(n)
        if v == 1: return even_money_bet("Low (1-18)",   list(range(1, 19)))
        if v == 2: return even_money_bet("High (19-36)", list(range(19, 37)))
        raise CSVImportError(f"Low/High: 1=Low 2=High, got {v}")

    else:
        raise CSVImportError(f"Unknown bet type code: {t} (valid: 1-11)")


def load_csv(path: str, bankroll: float) -> list[tuple[Bet, float]]:
    if not os.path.isfile(path):
        raise CSVImportError(f"File not found: {path}")

    bets, total, errors = [], 0.0, 0
    with open(path, newline="") as fh:
        for line_num, row in enumerate(csv.reader(fh), start=1):
            if not row or row[0].strip().startswith("#"):
                continue
            if len(row) != 3:
                console.print(f"  [yellow]⚠[/]  Line {line_num}: expected 3 columns, got {len(row)} — skipped")
                errors += 1; continue
            raw_type, raw_num, raw_amt = row
            try:
                type_code = int(raw_type.strip())
            except ValueError:
                console.print(f"  [yellow]⚠[/]  Line {line_num}: invalid type code '{raw_type.strip()}' — skipped")
                errors += 1; continue
            try:
                amount = float(raw_amt.strip())
                if amount <= 0: raise ValueError
            except ValueError:
                console.print(f"  [yellow]⚠[/]  Line {line_num}: invalid amount '{raw_amt.strip()}' — skipped")
                errors += 1; continue
            try:
                bet = bet_from_row(type_code, raw_num, amount)
            except CSVImportError as e:
                console.print(f"  [yellow]⚠[/]  Line {line_num}: {e} — skipped")
                errors += 1; continue
            if total + amount > bankroll:
                console.print(f"  [yellow]⚠[/]  Line {line_num}: adding ${amount:.2f} exceeds bankroll — skipped")
                errors += 1; continue
            bets.append((bet, amount))
            total += amount

    if errors:
        console.print(f"  [dim]ℹ  {errors} row(s) skipped.[/]")
    return bets


def print_csv_reference():
    t = Table(
        title="[bold cyan]CSV Bet Format  —  type_code, number, amount[/]",
        box=box.SIMPLE_HEAVY,
        border_style="cyan",
        show_lines=True,
        min_width=56,
    )
    t.add_column("Code", style="bold yellow", justify="center", width=6)
    t.add_column("Bet Type",    style="bold white")
    t.add_column("Payout", justify="center", style="green")
    t.add_column("Number column", style="dim white")

    rows = [
        ("1",  "Straight up",      "35:1", "0–36 or 00"),
        ("2",  "Split",            "17:1", "Lowest adjacent number"),
        ("3",  "Street",           "11:1", "Row 1–12"),
        ("4",  "Corner",            "8:1", "Top-left number"),
        ("5",  "Line",              "5:1", "Starting row 1–11"),
        ("6",  "Five Number",       "6:1", "Any (ignored)"),
        ("7",  "Dozen",             "2:1", "1, 2, or 3"),
        ("8",  "Column",            "2:1", "1, 2, or 3"),
        ("9",  "Red / Black",       "1:1", "1 = Red,  2 = Black"),
        ("10", "Even / Odd",        "1:1", "1 = Even, 2 = Odd"),
        ("11", "Low / High",        "1:1", "1 = Low,  2 = High"),
    ]
    for r in rows:
        t.add_row(*r)
    console.print()
    console.print(Align.center(t))
    console.print()

# ─────────────────────────────────────────────
#  Bet builder menu
# ─────────────────────────────────────────────

def show_bet_menu():
    t = Table(
        title="[bold gold1]Place Your Bet[/]",
        box=box.ROUNDED,
        border_style="gold1",
        show_header=False,
        min_width=48,
        show_lines=False,
    )
    t.add_column("Key",  style="bold yellow",  justify="right", width=4)
    t.add_column("Bet",  style="white",        width=26)
    t.add_column("Odds", style="bold green",   justify="right")

    inside = [
        ("1", "Straight up",            "35:1"),
        ("2", "Split",                  "17:1"),
        ("3", "Street",                 "11:1"),
        ("4", "Corner",                  "8:1"),
        ("5", "Line / Double Street",    "5:1"),
        ("6", "Five Number (0/00/1/2/3)","6:1"),
    ]
    outside = [
        ("7",  "Dozen",            "2:1"),
        ("8",  "Column",           "2:1"),
        ("9",  "Red / Black",      "1:1"),
        ("10", "Even / Odd",       "1:1"),
        ("11", "Low / High",       "1:1"),
    ]

    t.add_row("[dim]──[/]", "[dim italic]Inside Bets[/]", "")
    for key, name, odds in inside:
        t.add_row(key, name, odds)
    t.add_row("[dim]──[/]", "[dim italic]Outside Bets[/]", "")
    for key, name, odds in outside:
        t.add_row(key, name, odds)
    t.add_row("0",  "[dim]Done adding bets[/]", "")

    console.print()
    console.print(Align.center(t))


def choose_bet(bankroll: float) -> Optional[tuple[Bet, float]]:
    show_bet_menu()
    choice = prompt_int("Choice:", 0, 11)
    if choice == 0:
        return None

    if choice == 1:
        n = prompt_number_on_board("Straight-up number (0-36 or 00):")
        bet = straight_bet(n)

    elif choice == 2:
        console.print("  [dim]Enter two adjacent numbers for a split.[/]")
        a = prompt_number_on_board("First number:")
        b = prompt_number_on_board("Second number:")
        if not are_adjacent_split(a, b):
            console.print("  [red]⚠  Those numbers are not adjacent.[/]")
            return None
        bet = split_bet(a, b)

    elif choice == 3:
        r = prompt_int("Row number (1-12):", 1, 12)
        bet = street_bet(r)

    elif choice == 4:
        console.print("  [dim]Enter the top-left number of the 2×2 square.[/]")
        tl = prompt_number_on_board("Top-left number:")
        if not isinstance(tl, int) or tl < 1:
            console.print("  [red]⚠  Corner bets cannot include 0 or 00.[/]")
            return None
        col_pos = ((tl - 1) % 3) + 1
        row_num  = (tl - 1) // 3 + 1
        if col_pos == 3 or row_num > 11:
            console.print("  [red]⚠  That number can't be the top-left of a corner.[/]")
            return None
        bet = corner_bet(tl, tl+1, tl+3, tl+4)

    elif choice == 5:
        r = prompt_int("Starting row (1-11):", 1, 11)
        bet = line_bet(r)

    elif choice == 6:
        bet = FIVE_NUMBER

    elif choice == 7:
        d = prompt_int("Dozen (1=1-12, 2=13-24, 3=25-36):", 1, 3)
        bet = dozen_bet(d)

    elif choice == 8:
        c = prompt_int("Column (1, 2, or 3):", 1, 3)
        bet = column_bet(c)

    elif choice == 9:
        rb = console.input("  [cyan]Red or Black? (r/b):[/] ").strip().lower()
        if rb == "r":   bet = even_money_bet("Red",   list(RED_NUMBERS))
        elif rb == "b": bet = even_money_bet("Black", list(BLACK_NUMBERS))
        else:           console.print("  [red]Invalid.[/]"); return None

    elif choice == 10:
        eo = console.input("  [cyan]Even or Odd? (e/o):[/] ").strip().lower()
        if eo == "e":   bet = even_money_bet("Even", [x for x in range(2, 37, 2)])
        elif eo == "o": bet = even_money_bet("Odd",  [x for x in range(1, 37, 2)])
        else:           console.print("  [red]Invalid.[/]"); return None

    elif choice == 11:
        lh = console.input("  [cyan]Low (1-18) or High (19-36)? (l/h):[/] ").strip().lower()
        if lh == "l":   bet = even_money_bet("Low (1-18)",   list(range(1, 19)))
        elif lh == "h": bet = even_money_bet("High (19-36)", list(range(19, 37)))
        else:           console.print("  [red]Invalid.[/]"); return None

    amount = prompt_float(f"Wager (max ${bankroll:,.2f}): $", 1, bankroll)
    return bet, amount

# ─────────────────────────────────────────────
#  Bet display helpers
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
#  Double-down logic
# ─────────────────────────────────────────────

def apply_double_down(
    bets: list[tuple[Bet, float]],
    bankroll_available: float,
) -> tuple[list[tuple[Bet, float]], float]:
    """
    Double every wager in *bets*, capped so the total extra cost never
    exceeds *bankroll_available*.  Returns (new_bets, extra_cost).

    If even a partial double is impossible (bankroll_available < $1),
    returns the original list unchanged and extra_cost = 0.
    """
    current_total = sum(a for _, a in bets)
    max_extra     = bankroll_available          # most we can spend doubling

    if max_extra < 1:
        console.print("  [red]⚠  Not enough bankroll to double any bet.[/]")
        return bets, 0.0

    # Ideal: double every bet (extra = current_total)
    if current_total <= max_extra:
        new_bets   = [(b, a * 2) for b, a in bets]
        extra_cost = current_total
    else:
        # Scale all bets proportionally so extra == max_extra
        scale      = max_extra / current_total
        new_bets   = [(b, round(a * (1 + scale), 2)) for b, a in bets]
        extra_cost = round(max_extra, 2)
        console.print(
            f"  [yellow]⚠  Full double would exceed bankroll. "
            f"Bets scaled to ×{1 + scale:.2f} instead.[/]"
        )

    return new_bets, extra_cost


def prompt_double_down(
    bets: list[tuple[Bet, float]],
    bankroll: float,
) -> tuple[list[tuple[Bet, float]], float]:
    """
    Show the double-down prompt.  Returns (updated_bets, extra_cost_deducted).
    extra_cost is 0 if the player declines.
    """
    current_total = sum(a for _, a in bets)
    ideal_extra   = current_total
    can_full      = ideal_extra <= bankroll

    console.print()
    if can_full:
        console.print(
            f"  [bold gold1]🎲 Double Down[/]  —  double all wagers "
            f"([yellow]+${ideal_extra:,.2f}[/] from bankroll of [yellow]${bankroll:,.2f}[/])"
        )
    else:
        console.print(
            f"  [bold gold1]🎲 Double Down[/]  —  partial double available "
            f"([yellow]+${bankroll:,.2f}[/] max, bankroll: [yellow]${bankroll:,.2f}[/])"
        )

    confirm = console.input("  Double down? [cyan](y/n)[/]: ").strip().lower()
    if confirm != "y":
        return bets, 0.0

    new_bets, extra = apply_double_down(bets, bankroll)
    print_bet_summary(new_bets, title="Bets After Double Down 🎲")
    return new_bets, extra


def print_bet_summary(bets: list[tuple[Bet, float]], title: str = "Current Bets"):
    t = Table(
        title=f"[bold cyan]{title}[/]",
        box=box.SIMPLE_HEAVY,
        border_style="cyan",
        show_lines=False,
        min_width=48,
    )
    t.add_column("#",       style="dim",          justify="right", width=3)
    t.add_column("Bet",     style="bold white")
    t.add_column("Payout",  style="green",        justify="center", width=8)
    t.add_column("Wager",   style="yellow",       justify="right",  width=10)

    total = 0.0
    for i, (bet, amt) in enumerate(bets, 1):
        t.add_row(str(i), bet.name, f"{bet.payout}:1", f"${amt:,.2f}")
        total += amt
    t.add_section()
    t.add_row("", "[bold]Total[/]", "", f"[bold yellow]${total:,.2f}[/]")
    console.print()
    console.print(Align.center(t))


def print_results_table(bets: list[tuple[Bet, float]], outcome, spin_net: float, bankroll: float):
    col = pocket_color(outcome) if isinstance(outcome, int) else "green"
    color_name = "Red" if col == "red" else ("Black" if col == "white" else "Green")
    outcome_str = str(outcome)

    t = Table(
        title=f"[bold]Outcome: [bold {col}]{outcome_str}[/]  [dim]({color_name})[/][/]",
        box=box.DOUBLE_EDGE,
        border_style="gold1",
        show_lines=True,
        min_width=52,
    )
    t.add_column("",       width=3,  justify="center")
    t.add_column("Bet",    style="white")
    t.add_column("Wager",  justify="right", style="yellow",  width=10)
    t.add_column("Result", justify="right",                  width=12)

    for bet, amount in bets:
        if outcome in bet.numbers:
            profit = amount * bet.payout
            t.add_row("✅", bet.name, f"${amount:,.2f}", f"[bold green]+${profit:,.2f}[/]")
        else:
            t.add_row("❌", bet.name, f"${amount:,.2f}", f"[bold red]-${amount:,.2f}[/]")

    t.add_section()
    net_style = "bold green" if spin_net >= 0 else "bold red"
    sign = "+" if spin_net >= 0 else ""
    t.add_row(
        "", "[bold]Net this spin[/]", "",
        f"[{net_style}]{sign}${spin_net:,.2f}[/]"
    )
    t.add_row(
        "", "[bold]New bankroll[/]", "",
        f"[bold yellow]${bankroll:,.2f}[/]"
    )

    console.print()
    console.print(Align.center(t))

# ─────────────────────────────────────────────
#  Observation spin (no bet)
# ─────────────────────────────────────────────

def do_observation_spin(history: "SpinHistory") -> None:
    """Spin the wheel with no money on the table and record the result."""
    console.print()
    console.print(Rule("[yellow]🔍  Observation Spin  —  No Bet[/]", style="yellow"))
    outcome = random.choice(WHEEL)
    spin_animation(outcome)
    history.add(outcome, wagered=False)

    col        = pocket_color(outcome) if isinstance(outcome, int) else "green"
    rich_col   = "red" if col == "red" else ("bright_white" if col == "white" else "green")
    color_name = "Red" if col == "red" else ("Black" if col == "white" else "Green")

    t = Table(box=box.ROUNDED, border_style="yellow", show_header=False, min_width=38)
    t.add_column("Label", style="dim",        width=16)
    t.add_column("Value", justify="right")
    t.add_row("Pocket",       f"[bold {rich_col}]{str(outcome):>2}[/]")
    t.add_row("Color",        f"[bold {rich_col}]{color_name}[/]")
    t.add_row("Parity",
              "[dim]—[/]" if not isinstance(outcome, int) or outcome == 0
              else ("[cyan]Even[/]" if outcome % 2 == 0 else "[magenta]Odd[/]"))
    t.add_row("Range",
              "[dim]—[/]" if not isinstance(outcome, int) or outcome == 0
              else ("[blue]Low (1-18)[/]" if outcome <= 18 else "[orange3]High (19-36)[/]"))
    t.add_row("Observations recorded", str(sum(1 for r in history.records if not r.wagered)))
    console.print()
    console.print(Align.center(t))
    console.print(f"  [dim]Tip: use [cyan](h)[/] history to review the full spin log.[/]")


# ─────────────────────────────────────────────
#  Repeat last bet
# ─────────────────────────────────────────────

def _apply_repeat_bet(
    last_bets: list[tuple["Bet", float]],
    bankroll: float,
) -> tuple[list[tuple["Bet", float]], float]:
    """
    Re-use last_bets against the current bankroll.
    - Full repeat if bankroll covers the total.
    - Proportional scale-down if bankroll is short but >= $1 per bet.
    - Returns ([], 0.0) and prints a warning if nothing is affordable.
    """
    original_total = sum(a for _, a in last_bets)

    if original_total <= bankroll:
        console.print(
            f"  [green]✓[/]  Repeating last layout  "
            f"([yellow]${original_total:,.2f}[/] total)"
        )
        return list(last_bets), original_total

    # Scale proportionally
    if bankroll < 1.0:
        console.print("  [red]⚠  Bankroll too low to repeat any bet.[/]")
        return [], 0.0

    scale     = bankroll / original_total
    new_bets  = [(b, max(0.01, round(a * scale, 2))) for b, a in last_bets]
    new_total = sum(a for _, a in new_bets)
    console.print(
        f"  [yellow]⚠  Bankroll short — bets scaled to "
        f"×{scale:.2f} ([yellow]${new_total:,.2f}[/] total)[/]"
    )
    return new_bets, new_total


# ─────────────────────────────────────────────
#  CSV load wrapper
# ─────────────────────────────────────────────

def _collect_bets_csv(path: str, bankroll: float) -> list[tuple[Bet, float]]:
    try:
        bets = load_csv(path, bankroll)
    except CSVImportError as e:
        console.print(f"  [bold red]✖  CSV error:[/] {e}")
        return []
    if not bets:
        console.print("  [yellow]⚠  No valid bets loaded from CSV.[/]")
    else:
        print_bet_summary(bets, title=f"CSV Layout  —  {os.path.basename(path)}")
    return bets


def _collect_bets_manually(bankroll: float) -> Optional[tuple[list[tuple[Bet, float]], float]]:
    """
    Returns (bets, total_wagered) or None if the user quits.
    total_wagered already includes any double-down extra.
    """
    bets, total_wagered = [], 0.0
    while True:
        result = choose_bet(bankroll - total_wagered)
        if result is None:
            if not bets:
                q = console.input("\n  [dim]No bets placed. (q)uit or (c)ontinue?[/] ").strip().lower()
                if q == "q": return None
                continue
            break
        bet, amount = result
        bets.append((bet, amount))
        total_wagered += amount
        console.print(f"  [green]✓[/]  {bet.name} — [yellow]${amount:,.2f}[/]  [dim]({bet.payout}:1)[/]")
        console.print(f"     [dim]Total wagered this spin: [yellow]${total_wagered:,.2f}[/][/]")
        more = console.input(
            "  [dim]Add another bet? ([/][cyan]y[/][dim]) "
            "  Double down? ([/][cyan]d[/][dim]) "
            "  Done? ([/][cyan]n[/][dim]):[/] "
        ).strip().lower()
        if more == "d":
            bets, extra = prompt_double_down(bets, bankroll - total_wagered)
            total_wagered += extra
            break
        elif more != "y" or total_wagered >= bankroll:
            break

    # Offer double-down at the end if not already doubled
    if bets and total_wagered < bankroll:
        print_bet_summary(bets, title="Final Bet Layout")
        dd = console.input(
            "  [cyan](s)[/]pin  [cyan](d)[/]ouble down  → "
        ).strip().lower()
        if dd == "d":
            bets, extra = prompt_double_down(bets, bankroll - total_wagered)
            total_wagered += extra

    return bets, total_wagered


def _resolve_spin_bets(bankroll: float, csv_path: Optional[str],
                        preset_bets: list) -> tuple[list, float, str]:
    """
    Returns (bets, total_wagered, action).
    action in ('spin', 'quit', 'reload', 'manual').
    total_wagered is already the full amount to deduct (including any double).
    """
    if csv_path and preset_bets:
        csv_total = sum(a for _, a in preset_bets)
        print_bet_summary(preset_bets, title="CSV Layout  (active)")
        if csv_total > bankroll:
            console.print(f"  [red]⚠  Bankroll too low for CSV layout — switching to manual.[/]")
        else:
            action = console.input(
                "\n  [cyan](s)[/]pin  [cyan](d)[/]ouble down  "
                "[cyan](m)[/]anual override  "
                "[cyan](r)[/]eload CSV  [cyan](q)[/]uit  → "
            ).strip().lower()
            if action == "q": return [], 0.0, "quit"
            if action == "m": return [], 0.0, "manual"
            if action == "r": return [], 0.0, "reload"
            if action == "d":
                bets, extra = prompt_double_down(preset_bets, bankroll - csv_total)
                return bets, sum(a for _, a in bets), "spin"
            return preset_bets, csv_total, "spin"

    result = _collect_bets_manually(bankroll)
    if result is None:
        return [], 0.0, "quit"
    bets, total_wagered = result
    return bets, total_wagered, "spin"

# ─────────────────────────────────────────────
#  Main game loop
# ─────────────────────────────────────────────

def play():
    title_banner()

    console.print("  [dim]Welcome! Set your starting bankroll.[/]")
    bankroll = prompt_float("Starting bankroll: $", 1, 1_000_000)

    csv_path:    Optional[str]            = None
    preset_bets: list[tuple[Bet, float]] = []

    console.print()
    use_csv = console.input("  [cyan]Load a CSV bet layout? (y/n):[/] ").strip().lower()
    if use_csv == "y":
        print_csv_reference()
        csv_path    = console.input("  [cyan]CSV file path:[/] ").strip()
        preset_bets = _collect_bets_csv(csv_path, bankroll)
        if not preset_bets:
            console.print("  [dim]Falling back to manual mode.[/]")
            csv_path = None

    stats     = Stats(starting_bankroll=bankroll)
    history   = SpinHistory()
    spin_num  = 0
    last_bets: list[tuple["Bet", float]] = []   # last live bet layout

    while True:
        console.print()
        print_bankroll_header(bankroll, spin_num + 1, history)

        if bankroll < 1:
            console.print("\n  [bold red]You're out of chips. Session over.[/]\n")
            break

        # Offer observe/history/repeat before betting
        repeat_hint = "  [cyan](r)[/]epeat last  " if last_bets else ""
        pre = console.input(
            f"  [cyan](b)[/]et  {repeat_hint}[cyan](o)[/]bserve  "
            "[cyan](h)[/]istory  [cyan](q)[/]uit  → "
        ).strip().lower()
        if pre == "q":
            stats.summary(bankroll)
            console.print("\n  [dim]Thanks for playing. Good luck! 🎰[/]\n")
            return
        if pre == "o":
            do_observation_spin(history)
            continue
        if pre == "h":
            history.print_table()
            continue
        if pre == "r":
            if not last_bets:
                console.print("  [yellow]⚠  No previous bet to repeat yet.[/]")
                continue
            bets, total_wagered = _apply_repeat_bet(last_bets, bankroll)
            if not bets:
                continue
            # allow double-down on repeated bets too
            print_bet_summary(bets, title="Repeated Bet Layout 🔁")
            dd = console.input(
                "  [cyan](s)[/]pin  [cyan](d)[/]ouble down  → "
            ).strip().lower()
            if dd == "d":
                bets, extra = prompt_double_down(bets, bankroll - total_wagered)
                total_wagered += extra
            bankroll -= total_wagered
            console.print()
            outcome = random.choice(WHEEL)
            spin_animation(outcome)
            spin_num += 1
            spin_net = -total_wagered
            for bet, amount in bets:
                if outcome in bet.numbers:
                    spin_net += amount * bet.payout + amount
                    bankroll += amount * bet.payout + amount
            print_results_table(bets, outcome, spin_net, bankroll)
            stats.record(spin_num, outcome, spin_net, total_wagered)
            history.add(outcome, wagered=True, net=spin_net)
            last_bets = [(b, a) for b, a in bets]
            console.print()
            next_action = console.input(
                "  [cyan](s)[/]pin again  [cyan](t)[/]able stats  "
                "[cyan](h)[/]istory  [cyan](q)[/]uit  → "
            ).strip().lower()
            if next_action == "q":
                break
            elif next_action == "t":
                stats.summary(bankroll)
            elif next_action == "h":
                history.print_table()
            continue

        bets, total_wagered, action = _resolve_spin_bets(bankroll, csv_path, preset_bets)

        if action == "quit":
            stats.summary(bankroll)
            console.print("\n  [dim]Thanks for playing. Good luck! 🎰[/]\n")
            return

        if action == "reload":
            preset_bets = _collect_bets_csv(csv_path, bankroll)
            if preset_bets:
                bets = preset_bets
                total_wagered = sum(a for _, a in bets)
            else:
                result = _collect_bets_manually(bankroll)
                if result is None: continue
                bets, total_wagered = result
            if not bets: continue

        if action == "manual":
            result = _collect_bets_manually(bankroll)
            if result is None:
                stats.summary(bankroll)
                console.print("\n  [dim]Thanks for playing. Good luck! 🎰[/]\n")
                return
            bets, total_wagered = result

        if not bets:
            continue

        bankroll -= total_wagered

        # Spin
        console.print()
        outcome = random.choice(WHEEL)
        spin_animation(outcome)
        spin_num += 1

        # Evaluate
        spin_net = -total_wagered
        for bet, amount in bets:
            if outcome in bet.numbers:
                spin_net += amount * bet.payout + amount
                bankroll += amount * bet.payout + amount

        print_results_table(bets, outcome, spin_net, bankroll)
        stats.record(spin_num, outcome, spin_net, total_wagered)
        history.add(outcome, wagered=True, net=spin_net)
        last_bets = [(b, a) for b, a in bets]   # remember for repeat

        console.print()
        next_action = console.input(
            "  [cyan](s)[/]pin again  [cyan](t)[/]able stats  [cyan](h)[/]istory  [cyan](q)[/]uit  → "
        ).strip().lower()
        if next_action == "q":
            break
        elif next_action == "t":
            stats.summary(bankroll)
        elif next_action == "h":
            history.print_table()

    stats.summary(bankroll)
    console.print("\n  [dim]Thanks for playing. Gamble responsibly. 🎰[/]\n")


if __name__ == "__main__":
    play()