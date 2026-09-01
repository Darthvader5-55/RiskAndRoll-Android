"""
game/over_under.py
------------------
OVER / UNDER: bet on the TOTAL of all six dice, not on one colour.

Six dice add up to somewhere between 6 and 36, and the middle number is 21.
The player bets one of three things:

    UNDER    the total comes to 20 or less
    OVER     the total comes to 22 or more
    EXACTLY  the total is exactly 21

WHY THIS MODE EXISTS
    Color Royale asks for a colour AND a number, which is a 1 in 6 shot, so
    players lose five rounds out of six. Here OVER and UNDER are each close to
    a coin flip, so a queue actually wins things and stays at the booth.

THE NUMBERS ARE REAL
    These are not guesses. They were counted by going through all 46,656 ways
    six dice can land:

        UNDER (20 or less)   21,168 ways   45.36%
        EXACTLY 21            4,332 ways    9.28%
        OVER (22 or more)    21,168 ways   45.36%

    A perfectly fair payout would be 2.205x for over/under and 10.77x for the
    exact hit. The payouts below are a little under fair, which is where the
    booth's margin comes from. Say that plainly if anyone asks - it is a much
    better answer than pretending it is even.

Like betting.py, there is no drawing code here at all.
"""

UNDER = "UNDER"
OVER = "OVER"
EXACT = "EXACT"

MIDDLE = 21             # the balance point of six dice

# What a winning bet pays back, per credit staked.
PAYOUT = {
    UNDER: 2,           # fair would be 2.205 -> about a 9% booth margin
    OVER: 2,
    EXACT: 9,           # fair would be 10.77 -> about a 16% booth margin
}

# The real chances, counted rather than estimated. Shown on screen so players
# can see what they are choosing.
CHANCE = {
    UNDER: 0.4536,
    OVER: 0.4536,
    EXACT: 0.0928,
}

CHOICES = [UNDER, EXACT, OVER]


def describe(choice):
    """A short line explaining a choice, for the screen."""
    if choice == UNDER:
        return f"TOTAL {MIDDLE - 1} OR LESS"
    if choice == OVER:
        return f"TOTAL {MIDDLE + 1} OR MORE"
    return f"TOTAL EXACTLY {MIDDLE}"


def result_for(total):
    """Which of the three choices this total actually was."""
    if total < MIDDLE:
        return UNDER
    if total > MIDDLE:
        return OVER
    return EXACT


class OverUnderGame:
    """Credits and bet rules for one player at the booth."""

    def __init__(self, credits, starting_credits=None):
        self.starting_credits = (starting_credits if starting_credits is not None
                                 else credits)
        self.credits = credits
        self.choice = None
        self.amount = None
        self.last_result = None

    # ================================================================ choosing
    def select_choice(self, choice):
        if choice in PAYOUT:
            self.choice = choice

    def select_amount(self, amount):
        self.amount = amount

    def clear(self):
        self.choice = None
        self.amount = None

    @property
    def is_complete(self):
        return self.choice is not None and self.amount is not None

    def validate(self):
        """Returns (ok, message). Same shape as betting.py on purpose."""
        if self.choice is None:
            return False, "CHOOSE OVER, UNDER OR EXACT"
        if self.amount is None:
            return False, "CHOOSE A BET AMOUNT"
        if self.amount <= 0:
            return False, "BET MUST BE MORE THAN ZERO"
        if self.amount > self.credits:
            return False, "NOT ENOUGH CREDITS"
        return True, "READY - PRESS PLACE BET"

    def can_afford(self, amount):
        return amount <= self.credits

    def can_afford_anything(self, amounts):
        return any(self.can_afford(amount) for amount in amounts)

    # ================================================================= playing
    def place(self):
        """Take the stake. Called once, when the roll starts."""
        ok, _message = self.validate()
        if not ok:
            return False
        self.credits -= self.amount
        return True

    def settle(self, results):
        """Work out the round from DiceSet.results() and pay out."""
        total = sum(results.values())
        landed = result_for(total)
        won = (landed == self.choice)

        payout = self.amount * PAYOUT[self.choice] if won else 0
        self.credits += payout

        self.last_result = {
            "won": won,
            "total": total,
            "choice": self.choice,
            "landed": landed,
            "bet": self.amount,
            "payout": payout,
            "change": payout - self.amount,
            "credits": self.credits,
            "results": dict(results),
        }
        return self.last_result

    def reset_credits(self):
        self.credits = self.starting_credits
        self.clear()
