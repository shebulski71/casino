"""
American Roulette — Terminal Edition
Full bet types, bankroll tracking, and session statistics.
"""

import random
import time
from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────────────────────────
#  Wheel layout
# ─────────────────────────────────────────────

# American wheel: 0, 00, 1-36
RED_NUMBERS = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
BLACK_NUMBERS = {2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35}

WHEEL = list(range(0, 37)) + ["00"]   # 38 pockets

# Layout rows (for street / corner validation)
# Row n contains numbers 3n-2, 3n-1, 3n  (n = 1..12)
ROWS = [[3*r-2, 3*r-1, 3*r] for r in range(1, 13)]
# Columns: col 1 = 1,4,7,...,34  col 2 = 2,5,...,35  col 3 = 3,6,...,36
COLUMNS = [[c + 3*r for r in range(0, 12)] for c in [1, 2, 3]]
DOZENS = [list(range(1, 13)), list(range(13, 25)), list(range(25, 37))]

def color(n):
    if n in RED_NUMBERS:   return "Red"
    if n in BLACK_NUMBERS: return "Black"
    return "Green"

def display_number(n):
    c = color(n) if isinstance(n, int) else "Green"
    code = "\033[91m" if c == "Red" else ("\033[90m" if c == "Black" else "\033[92m")
    return f"{code}{str(n):>2}\033[0m"

# ─────────────────────────────────────────────
#  Bet definitions
# ─────────────────────────────────────────────

@dataclass
class Bet:
    name: str
    numbers: list
    payout: int   # x to 1

def straight_bet(n) -> Bet:
    label = str(n)
    return Bet(f"Straight {label}", [n], 35)

def split_bet(a, b) -> Bet:
    return Bet(f"Split {a}/{b}", [a, b], 17)

def street_bet(row: int) -> Bet:
    nums = ROWS[row - 1]
    return Bet(f"Street {nums[0]}-{nums[2]}", nums, 11)

def corner_bet(a, b, c, d) -> Bet:
    return Bet(f"Corner {a}/{b}/{c}/{d}", [a, b, c, d], 8)

def line_bet(row: int) -> Bet:
    nums = ROWS[row - 1] + ROWS[row]
    return Bet(f"Line {nums[0]}-{nums[5]}", nums, 5)

def dozen_bet(d: int) -> Bet:
    nums = DOZENS[d - 1]
    return Bet(f"Dozen {d}st/nd/rd", nums, 2)

def column_bet(c: int) -> Bet:
    nums = COLUMNS[c - 1]
    return Bet(f"Column {c}", nums, 2)

def even_money_bet(name: str, numbers: list) -> Bet:
    return Bet(name, numbers, 1)

FIVE_NUMBER = Bet("Five Number (0,00,1,2,3)", [0, "00", 1, 2, 3], 6)

# ─────────────────────────────────────────────
#  Session stats
# ─────────────────────────────────────────────

@dataclass
class Stats:
    spins: int = 0
    wins: int = 0
    losses: int = 0
    pushes: int = 0       # unused in roulette but kept for symmetry
    total_wagered: float = 0.0
    total_won: float = 0.0
    biggest_win: float = 0.0
    biggest_loss: float = 0.0
    starting_bankroll: float = 0.0
    history: list = field(default_factory=list)  # (spin#, result, net)

    def record(self, spin: int, result, net: float, wagered: float):
        self.spins += 1
        self.total_wagered += wagered
        if net > 0:
            self.wins += 1
            self.total_won += net
            self.biggest_win = max(self.biggest_win, net)
        elif net < 0:
            self.losses += 1
            self.biggest_loss = min(self.biggest_loss, net)
        self.history.append((spin, result, net))

    def summary(self, bankroll: float):
        net = bankroll - self.starting_bankroll
        win_rate = (self.wins / self.spins * 100) if self.spins else 0
        edge = (self.total_won - self.total_wagered) / self.total_wagered * 100 if self.total_wagered else 0
        print("\n" + "═"*50)
        print("         📊  SESSION STATISTICS")
        print("═"*50)
        print(f"  Spins played    : {self.spins}")
        print(f"  Wins / Losses   : {self.wins} / {self.losses}")
        print(f"  Win rate        : {win_rate:.1f}%")
        print(f"  Total wagered   : ${self.total_wagered:,.2f}")
        print(f"  Net result      : {'+'if net>=0 else ''}{net:,.2f}")
        print(f"  Biggest win     : +${self.biggest_win:,.2f}")
        print(f"  Biggest loss    : ${self.biggest_loss:,.2f}")
        print(f"  Player edge     : {edge:.2f}%  (house edge ~5.26%)")
        print(f"  Final bankroll  : ${bankroll:,.2f}")
        print("═"*50)

# ─────────────────────────────────────────────
#  Helpers / UI
# ─────────────────────────────────────────────

def clear_line():
    print("\033[F\033[K", end="")

def title_banner():
    print("\n\033[93m" + "═"*50)
    print(r"""
   ____             _      _   _       
  |  _ \ ___  _   _| | ___| |_| |_ ___ 
  | |_) / _ \| | | | |/ _ \ __| __/ _ \\
  |  _ < (_) | |_| | |  __/ |_| ||  __/
  |_| \_\___/ \__,_|_|\___|\__|\__\___|
    American Casino Roulette — 00 Wheel
""")
    print("═"*50 + "\033[0m\n")

def spin_animation(result):
    frames = ["◐","◓","◑","◒"]
    for _ in range(12):
        for f in frames:
            print(f"\r  {f}  Spinning the wheel...", end="", flush=True)
            time.sleep(0.07)
    print(f"\r  ✦  Ball lands on:  {display_number(result)}  ({color(result) if isinstance(result, int) else 'Green'})          ")

def prompt_float(msg: str, lo: float, hi: float) -> float:
    while True:
        try:
            v = float(input(msg))
            if lo <= v <= hi:
                return v
            print(f"  Enter a value between {lo} and {hi}.")
        except ValueError:
            print("  Please enter a number.")

def prompt_int(msg: str, lo: int, hi: int) -> int:
    while True:
        try:
            v = int(input(msg))
            if lo <= v <= hi:
                return v
            print(f"  Enter a value between {lo} and {hi}.")
        except ValueError:
            print("  Please enter a whole number.")

def prompt_number_on_board(msg: str):
    """Return int 0-36 or '00'."""
    while True:
        raw = input(msg).strip()
        if raw == "00":
            return "00"
        try:
            n = int(raw)
            if 0 <= n <= 36:
                return n
        except ValueError:
            pass
        print("  Enter 0–36 or 00.")

def are_adjacent_split(a, b):
    """True if a and b are horizontally or vertically adjacent on the layout."""
    if not (isinstance(a, int) and isinstance(b, int) and a >= 1 and b >= 1):
        return False
    # horizontal neighbour (same row, consecutive)
    for row in ROWS:
        if a in row and b in row:
            if abs(row.index(a) - row.index(b)) == 1:
                return True
    # vertical neighbour (same column position, adjacent rows)
    if abs(a - b) == 3:
        return True
    return False

# ─────────────────────────────────────────────
#  Bet builder menu
# ─────────────────────────────────────────────

def choose_bet(bankroll: float) -> Optional[tuple[Bet, float]]:
    """Return (Bet, amount) or None to skip."""
    print("""
  ┌─────────────────────────────────────────┐
  │           SELECT BET TYPE               │
  ├─────────────────────────────────────────┤
  │  Inside bets                            │
  │   1) Straight up      (35:1)            │
  │   2) Split            (17:1)            │
  │   3) Street           (11:1)            │
  │   4) Corner            (8:1)            │
  │   5) Line / Double Street (5:1)         │
  │   6) Five Number 0/00/1/2/3 (6:1)      │
  │                                         │
  │  Outside bets                           │
  │   7) Dozen             (2:1)            │
  │   8) Column            (2:1)            │
  │   9) Red / Black       (1:1)            │
  │  10) Even / Odd        (1:1)            │
  │  11) Low (1-18) / High (19-36) (1:1)   │
  │                                         │
  │   0) Done adding bets                   │
  └─────────────────────────────────────────┘""")

    choice = prompt_int("  Your choice: ", 0, 11)
    if choice == 0:
        return None

    # ── Inside bets ──────────────────────────
    if choice == 1:
        n = prompt_number_on_board("  Straight-up number (0-36 or 00): ")
        bet = straight_bet(n)

    elif choice == 2:
        print("  Enter two adjacent numbers for a split.")
        a = prompt_number_on_board("  First number: ")
        b = prompt_number_on_board("  Second number: ")
        if not are_adjacent_split(a, b):
            print("  ⚠  Those numbers are not adjacent. Try again.")
            return None
        bet = split_bet(a, b)

    elif choice == 3:
        r = prompt_int("  Row number (1-12): ", 1, 12)
        bet = street_bet(r)

    elif choice == 4:
        print("  Enter four numbers forming a square on the layout.")
        nums = []
        for i in range(4):
            nums.append(prompt_number_on_board(f"  Number {i+1}: "))
        # Basic validation: all ints, span 2 rows and 2 columns
        if not all(isinstance(x, int) and x >= 1 for x in nums):
            print("  ⚠  Corner bets cannot include 0 or 00.")
            return None
        bet = corner_bet(*nums)

    elif choice == 5:
        r = prompt_int("  Starting row (1-11, covers that row and the next): ", 1, 11)
        bet = line_bet(r)

    elif choice == 6:
        bet = FIVE_NUMBER

    # ── Outside bets ─────────────────────────
    elif choice == 7:
        d = prompt_int("  Dozen (1=1-12, 2=13-24, 3=25-36): ", 1, 3)
        bet = dozen_bet(d)

    elif choice == 8:
        c = prompt_int("  Column (1, 2, or 3): ", 1, 3)
        bet = column_bet(c)

    elif choice == 9:
        rb = input("  Red or Black? (r/b): ").strip().lower()
        if rb == "r":
            bet = even_money_bet("Red", list(RED_NUMBERS))
        elif rb == "b":
            bet = even_money_bet("Black", list(BLACK_NUMBERS))
        else:
            print("  Invalid choice.")
            return None

    elif choice == 10:
        eo = input("  Even or Odd? (e/o): ").strip().lower()
        if eo == "e":
            bet = even_money_bet("Even", [n for n in range(2, 37, 2)])
        elif eo == "o":
            bet = even_money_bet("Odd", [n for n in range(1, 37, 2)])
        else:
            print("  Invalid choice.")
            return None

    elif choice == 11:
        lh = input("  Low (1-18) or High (19-36)? (l/h): ").strip().lower()
        if lh == "l":
            bet = even_money_bet("Low (1-18)", list(range(1, 19)))
        elif lh == "h":
            bet = even_money_bet("High (19-36)", list(range(19, 37)))
        else:
            print("  Invalid choice.")
            return None

    amount = prompt_float(f"  Amount to wager (max ${bankroll:,.2f}): $", 1, bankroll)
    return bet, amount

# ─────────────────────────────────────────────
#  Main game loop
# ─────────────────────────────────────────────

def play():
    title_banner()
    print("  Welcome! Set your starting bankroll.")
    bankroll = prompt_float("  Starting bankroll: $", 1, 1_000_000)

    stats = Stats(starting_bankroll=bankroll)
    spin_num = 0

    while True:
        print(f"\n{'─'*50}")
        print(f"  💰  Bankroll: \033[96m${bankroll:,.2f}\033[0m   |   Spin #{spin_num + 1}")
        print(f"{'─'*50}")

        if bankroll < 1:
            print("\n  You're out of chips. Session over.\n")
            break

        # Collect bets
        bets: list[tuple[Bet, float]] = []
        total_wagered = 0.0

        while True:
            result = choose_bet(bankroll - total_wagered)
            if result is None:
                if not bets:
                    # Offer quit
                    q = input("\n  No bets placed. (q)uit or (c)ontinue? ").strip().lower()
                    if q == "q":
                        stats.summary(bankroll)
                        print("\n  Thanks for playing. Good luck! 🎰\n")
                        return
                    continue
                break
            bet, amount = result
            bets.append((bet, amount))
            total_wagered += amount
            print(f"  ✓  {bet.name} — ${amount:,.2f}  (payout {bet.payout}:1)")
            print(f"     Total wagered this spin: ${total_wagered:,.2f}")

            another = input("  Add another bet? (y/n): ").strip().lower()
            if another != "y" or total_wagered >= bankroll:
                break

        # Deduct wagers
        bankroll -= total_wagered

        # Spin
        print()
        outcome = random.choice(WHEEL)
        spin_animation(outcome)
        spin_num += 1

        # Evaluate bets
        spin_net = -total_wagered   # start assuming loss
        print()
        print("  ┌──────────────────────────────────────────┐")
        print("  │  BET RESULTS                             │")
        print("  ├──────────────────────────────────────────┤")
        for bet, amount in bets:
            if outcome in bet.numbers:
                winnings = amount * bet.payout + amount   # return stake + profit
                spin_net += winnings
                bankroll += winnings
                print(f"  │  ✅ {bet.name:<28} +${amount * bet.payout:>7,.2f}  │")
            else:
                print(f"  │  ❌ {bet.name:<28}  ${amount:>7,.2f}  │")
        print("  ├──────────────────────────────────────────┤")
        sign = "+" if spin_net >= 0 else ""
        color_code = "\033[92m" if spin_net >= 0 else "\033[91m"
        print(f"  │  Net this spin: {color_code}{sign}${spin_net:,.2f}\033[0m")
        print(f"  │  New bankroll:  ${bankroll:,.2f}")
        print("  └──────────────────────────────────────────┘")

        stats.record(spin_num, outcome, spin_net, total_wagered)

        # Continue?
        print()
        action = input("  (s)pin again  |  (t)able stats  |  (q)uit  → ").strip().lower()
        if action == "q":
            break
        elif action == "t":
            stats.summary(bankroll)

    stats.summary(bankroll)
    print("\n  Thanks for playing. Gamble responsibly. 🎰\n")

if __name__ == "__main__":
    play()