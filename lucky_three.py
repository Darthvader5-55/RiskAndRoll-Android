"""
game/lucky_three.py
-------------------
LUCKY THREE — pick a number, pick three colours, get paid per hit.

    1. Choose a NUMBER, 1 to 6.
    2. Choose THREE of the six colours - these are your dice.
    3. Choose a BET.
    4. All six dice roll, but only YOUR three count.
       Every one of your dice showing your number is a hit.

        1 hit    pays 2x       3 hits   pays 10x
        2 hits   pays 3x       0 hits   you lose the bet

WHY THIS MODE REPLACED HIGHER OR LOWER
    Higher or Lower had a hole in it. With a 1 showing, calling HIGHER could
    not lose, and a player could cash out of any risky round for free. Patched
    it still felt mean: you were mostly being told what the odds were and then
    punished by them.

    This is the opposite. You get three real choices, all six dice roll so the
    machine still puts on a show, and you win something 42% of the time -
    nearly a coin flip, and far kinder than Color Royale's 1 in 6.

THE NUMBERS, COUNTED NOT GUESSED
    Your three dice can land 216 ways. Counting them all:

        0 hits   125 of 216   57.9%   lose
        1 hit     75 of 216   34.7%   pays 2x
        2 hits    15 of 216    6.9%   pays 3x
        3 hits     1 of 216    0.5%   pays 10x   <- the jackpot

    That works out to 94.9 credits back for every 100 staked, so the booth
    keeps about 5 in every 100 over a long day. That is a much gentler edge
    than Color Royale, which is deliberate: this is the mode to point a
    nervous player at.

As with betting.py there is no drawing code in this file at all.
"""

TEAM_SIZE = 3

# What a win pays back per credit staked, by number of hits.
PAYOUT = {1: 2, 2: 3, 3: 10}

# The real chances, from counting all 216 outcomes.
CHANCE = {0: 0.5787, 1: 0.3472, 2: 0.0694, 3: 0.0046}
WIN_CHANCE = 0.4213


def payout_for(hits):
    """Credits returned per credit staked. 0 hits returns nothing."""
    return PAYOUT.get(hits, 0)


class LuckyThreeGame:
    """Credits, the three chosen colours, and the bet rules."""

    def __init__(self, credits, starting_credits=None, all_colors=None):
        self.starting_credits = (starting_credits if starting_credits is not None
                                 else credits)
        self.credits = credits
        self.all_colors = list(all_colors or [])

        self.number = None
        self.colors = []
        self.amount = None
        self.last_result = None

        self.best_hits = 0        # most hits seen this session
        self.jackpots = 0

    # ================================================================ choosing
    def select_number(self, number):
        self.number = number

    def select_amount(self, amount):
        self.amount = amount

    def tap_color(self, color_name):
        """Take a colour, or give it back if you already have it.

        Three is the limit, so a fourth tap is simply ignored - the player
        gives one back first. That keeps the rule easy to say out loud.
        """
        if color_name in self.colors:
            self.colors.remove(color_name)
            return False
        if len(self.colors) >= TEAM_SIZE:
            return False
        self.colors.append(color_name)
        return True

    def clear_colors(self):
        self.colors = []

    def random_colors(self, rng=None):
        import random as _random
        shuffler = rng or _random
        pool = list(self.all_colors)
        shuffler.shuffle(pool)
        self.colors = sorted(pool[:TEAM_SIZE], key=self.all_colors.index)

    def clear(self):
        """Between rounds the colours are kept - most players stick with
        the same lucky three - but the number and the bet are cleared."""
        self.number = None
        self.amount = None

    @property
    def has_colors(self):
        return len(self.colors) == TEAM_SIZE

    @property
    def is_complete(self):
        return (self.has_colors and self.number is not None
                and self.amount is not None)

    # ================================================================ checking
    def validate(self):
        """Returns (ok, message)."""
        if not self.has_colors:
            return False, f"PICK {TEAM_SIZE - len(self.colors)} MORE COLOUR(S)"
        if self.number is None:
            return False, "CHOOSE YOUR NUMBER"
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
        """Count the hits among the player's three dice and pay out."""
        hit_colors = [name for name in self.colors
                      if results.get(name) == self.number]
        hits = len(hit_colors)

        multiplier = payout_for(hits)
        payout = self.amount * multiplier
        self.credits += payout

        self.best_hits = max(self.best_hits, hits)
        if hits == TEAM_SIZE:
            self.jackpots += 1

        self.last_result = {
            "won": hits > 0,
            "hits": hits,
            "hit_colors": hit_colors,
            "number": self.number,
            "colors": list(self.colors),
            "multiplier": multiplier,
            "bet": self.amount,
            "payout": payout,
            "change": payout - self.amount,
            "credits": self.credits,
            "jackpot": hits == TEAM_SIZE,
            "results": dict(results),
        }
        return self.last_result

    def reset_credits(self):
        self.credits = self.starting_credits
        self.clear()
