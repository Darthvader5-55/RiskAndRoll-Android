"""
game/betting.py
---------------
Credits and the Color Royale betting rules.

This file contains NO drawing code at all. You could run it in a plain Python
console and test every rule. Keeping the money logic apart from the buttons is
what makes it easy to explain and impossible to break by accident from the UI.

The credits are a gameplay score, not real money. Follow your school's event
rules for anything the booth hands out.
"""

from config import settings


class Betting:
    """Holds the player's credits and their current selection."""

    def __init__(self, credits=None):
        self.credits = settings.STARTING_CREDITS if credits is None else credits

        # what the player has picked so far (None = not chosen yet)
        self.color = None
        self.number = None
        self.amount = None

        # filled in once a round has been played
        self.last_result = None

    # ==================================================================== picks
    def select_color(self, color_name):
        self.color = color_name

    def select_number(self, number):
        self.number = number

    def select_amount(self, amount):
        self.amount = amount

    def clear_selection(self):
        self.color = self.number = self.amount = None

    @property
    def is_complete(self):
        """Has the player chosen all three things?"""
        return (self.color is not None
                and self.number is not None
                and self.amount is not None)

    # =============================================================== validation
    def validate(self):
        """Check the bet before any credits move.

        Returns (ok, message). The UI shows the message when ok is False.
        Every rule from the design document lives here, in one place.
        """
        if self.color is None:
            return False, "PICK A COLOUR"
        if self.number is None:
            return False, "PICK A NUMBER"
        if self.amount is None:
            return False, "PICK A BET"
        if self.amount <= 0:
            return False, "BET MUST BE MORE THAN 0"
        if self.amount > self.credits:
            return False, "NOT ENOUGH CREDITS"
        return True, ""

    def can_afford_anything(self):
        """False when the player cannot even place the smallest bet."""
        return self.credits >= min(settings.BET_AMOUNTS)

    # ==================================================================== round
    def place(self):
        """Take the bet out of the player's credits. Call once per round.

        The stake leaves the wallet the moment the dice are locked in, which
        is why a loss needs no further subtraction later.
        """
        ok, message = self.validate()
        if not ok:
            return False, message

        self.credits -= self.amount
        return True, ""

    def settle(self, results):
        """Work out win or lose from the six dice, and pay out.

        results is the dictionary from DiceSet.results(), e.g.
            {"RED": 3, "BLUE": 6, "GREEN": 2, ...}

        A win pays the stake back doubled: bet 50, receive 100, net +50.
        """
        actual = results[self.color]
        won = (actual == self.number)
        payout = self.amount * settings.WIN_MULTIPLIER if won else 0

        self.credits += payout

        self.last_result = {
            "won": won,
            "color": self.color,
            "number": self.number,
            "actual": actual,
            "bet": self.amount,
            "payout": payout,
            "change": payout - self.amount,
            "credits": self.credits,
            "results": dict(results),
        }
        return self.last_result

    # ================================================================== operator
    def reset_credits(self):
        """Booth operator tool: start a fresh player."""
        self.credits = settings.STARTING_CREDITS
        self.clear_selection()
        self.last_result = None

    def add_credits(self, amount):
        self.credits = max(0, self.credits + amount)
