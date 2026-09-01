"""
game/beat_house.py
------------------
BEAT THE HOUSE: one player against the machine.

The player CHOOSES which colours to roll and how many (1, 2 or 3). The machine
takes the same number of dice from whatever is left. Highest total wins, and a
draw returns the stake.

Choosing your own dice does not change the odds by even a fraction - every
colour is the same six-sided die - but it makes the round yours instead of
something that happens to you, and it lets a player keep a lucky colour.

WHY IT EXISTS
    Arcade Duel needs two people. This is the same game for someone standing
    at the booth on their own, which at a real intramurals booth is most of
    the queue.

A NOTE ON THE ODDS, WORTH KNOWING FOR THE DEFENCE
    Counted over all 46,656 possible pairs of rolls:

        player wins   45.36%
        machine wins  45.36%
        draw           9.28%

    Paying 2x on a win and returning the stake on a draw makes this mode
    EXACTLY fair - the booth neither gains nor loses over the long run. That
    is deliberate: it is the mode to point at when someone asks whether the
    booth is rigged. If you would rather it made money, set DRAW_RETURNS_STAKE
    to False and a draw goes to the machine.
"""

from game.duel import PLAYER_A, PLAYER_B, TIE

# The line-up the mode starts with. The player can change both which colours
# are theirs and how many dice each side rolls.
DEFAULT_PLAYER_COLORS = ["RED", "BLUE", "GREEN"]
DEFAULT_HOUSE_COLORS = ["YELLOW", "PURPLE", "ORANGE"]
COLOR_POOL = DEFAULT_PLAYER_COLORS + DEFAULT_HOUSE_COLORS
MAX_DICE = 3

# kept so older code and tests still work
PLAYER_COLORS = DEFAULT_PLAYER_COLORS
HOUSE_COLORS = DEFAULT_HOUSE_COLORS

WIN_PAYOUT = 2
DRAW_RETURNS_STAKE = True

# Counted, not estimated. See the note above.
CHANCE_WIN = 0.4536
CHANCE_DRAW = 0.0928


class BeatTheHouse:
    """Credits and the running score against the machine."""

    def __init__(self, credits, starting_credits=None, dice_count=MAX_DICE):
        self.starting_credits = (starting_credits if starting_credits is not None
                                 else credits)
        self.credits = credits
        self.amount = None

        # Which colours are yours, and how many dice each side rolls. The
        # game opens with the classic line-up so it is playable straight away;
        # the player changes it from the screen.
        self.dice_count = dice_count
        self.player_colors = list(DEFAULT_PLAYER_COLORS[:dice_count])
        self.house_colors = list(DEFAULT_HOUSE_COLORS[:dice_count])

        self.player_wins = 0
        self.house_wins = 0
        self.draws = 0
        self.last_result = None

    # =============================================================== choosing
    def set_dice_count(self, count):
        """Change how many dice each side rolls. Clears the picks."""
        self.dice_count = max(1, min(MAX_DICE, int(count)))
        self.clear_picks()

    def clear_picks(self):
        self.player_colors = []
        self.house_colors = []

    def owner(self, color_name):
        """"YOU", "HOUSE", or None if the colour is still free."""
        if color_name in self.player_colors:
            return "YOU"
        if color_name in self.house_colors:
            return "HOUSE"
        return None

    def tap(self, color_name):
        """Take a free colour, or give back one of your own.

        The machine's colours cannot be taken - it has already been dealt in.
        """
        if color_name in self.house_colors:
            return False
        if color_name in self.player_colors:
            self.player_colors.remove(color_name)
            self.house_colors = []          # deal the machine again later
            return True
        if len(self.player_colors) >= self.dice_count:
            return False
        self.player_colors.append(color_name)
        if len(self.player_colors) == self.dice_count:
            self._deal_house()
        return True

    def _deal_house(self, rng=None):
        """Give the machine the same number of dice from what is left."""
        import random as _random
        shuffler = rng or _random
        left = [name for name in COLOR_POOL if name not in self.player_colors]
        shuffler.shuffle(left)
        self.house_colors = sorted(left[:self.dice_count], key=COLOR_POOL.index)

    def randomise(self, rng=None):
        """Older name for random_picks, kept so existing calls still work."""
        return self.random_picks(rng)

    def random_picks(self, rng=None):
        """Deal both sides at random."""
        import random as _random
        shuffler = rng or _random
        pool = list(COLOR_POOL)
        shuffler.shuffle(pool)
        self.player_colors = sorted(pool[:self.dice_count], key=COLOR_POOL.index)
        self._deal_house(rng)

    def in_play(self):
        return self.player_colors + self.house_colors

    @property
    def teams_ready(self):
        return (len(self.player_colors) == self.dice_count
                and len(self.house_colors) == self.dice_count)

    # ================================================================ betting
    def select_amount(self, amount):
        self.amount = amount

    def can_afford(self, amount):
        return amount <= self.credits

    def can_afford_anything(self, amounts):
        return any(self.can_afford(amount) for amount in amounts)

    def validate(self):
        if not self.teams_ready:
            return False, "PICK YOUR DICE"
        if self.amount is None:
            return False, "CHOOSE A BET AMOUNT"
        if self.amount <= 0:
            return False, "BET MUST BE MORE THAN ZERO"
        if self.amount > self.credits:
            return False, "NOT ENOUGH CREDITS"
        return True, "READY - PRESS ROLL"

    def place(self):
        ok, _message = self.validate()
        if not ok:
            return False
        self.credits -= self.amount
        return True

    # ================================================================ playing
    def judge(self, results):
        """Work out the round from DiceSet.results()."""
        player_total = sum(results[color] for color in self.player_colors)
        house_total = sum(results[color] for color in self.house_colors)

        if player_total > house_total:
            winner = PLAYER_A
            payout = self.amount * WIN_PAYOUT
            self.player_wins += 1
        elif house_total > player_total:
            winner = PLAYER_B
            payout = 0
            self.house_wins += 1
        else:
            winner = TIE
            payout = self.amount if DRAW_RETURNS_STAKE else 0
            self.draws += 1

        self.credits += payout

        self.last_result = {
            "winner": winner,
            "player_total": player_total,
            "house_total": house_total,
            "difference": abs(player_total - house_total),
            "bet": self.amount,
            "payout": payout,
            "change": payout - self.amount,
            "credits": self.credits,
            "results": dict(results),
            "player_colors": list(self.player_colors),
            "house_colors": list(self.house_colors),
            "score": (self.player_wins, self.house_wins, self.draws),
            "player_colors": list(self.player_colors),
            "house_colors": list(self.house_colors),
        }
        return self.last_result

    def reset_credits(self):
        self.credits = self.starting_credits

    def reset_score(self):
        self.player_wins = self.house_wins = self.draws = 0
