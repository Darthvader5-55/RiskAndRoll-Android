"""
game/duel.py
------------
Arcade Duel: 1 vs 1.

Before rolling, the two players CHOOSE their own colours by taking turns, and
they choose how many dice each side gets (1, 2 or 3). Then both sides roll at
once, each adds up their dice, and the highest total wins. Equal totals means
a rematch.

Nobody can take a colour that is already taken, and each side always ends up
with the same number of dice, so the duel is always fair.

Like betting.py this file has no drawing in it, so the rules can be tested
on their own.
"""

# The six colours, and the most dice one player can have (six colours shared
# between two players). Players choose their own colours in the setup screen,
# so these lists are only the order things appear in, not a fixed line-up.
PLAYER_A_COLORS = ["RED", "BLUE", "GREEN"]
PLAYER_B_COLORS = ["YELLOW", "PURPLE", "ORANGE"]
TEAM_SIZE = 3

# every colour a player can choose from
COLOR_POOL = PLAYER_A_COLORS + PLAYER_B_COLORS

PLAYER_A = "A"
PLAYER_B = "B"
TIE = "TIE"


class Duel:
    """Keeps the two teams and the running score across rounds."""

    def __init__(self, dice_count=TEAM_SIZE):
        self.wins = {PLAYER_A: 0, PLAYER_B: 0}
        self.rematches = 0
        self.last_result = None

        # How many dice each side rolls, and which colours they picked.
        self.dice_count = dice_count
        self.team_a = []
        self.team_b = []

    # ================================================================= choosing
    def set_dice_count(self, count):
        """Change how many dice each side rolls (1, 2 or 3).

        This clears the picks, because 'three each' and 'one each' are
        different games and half-filled teams would be confusing.
        """
        self.dice_count = max(1, min(TEAM_SIZE, int(count)))
        self.clear_teams()

    def clear_teams(self):
        """Empty both teams so the players can pick from scratch."""
        self.team_a = []
        self.team_b = []

    def colors(self, player):
        return self.team_a if player == PLAYER_A else self.team_b

    def owner(self, color_name):
        """PLAYER_A, PLAYER_B, or None if nobody has taken this colour yet."""
        if color_name in self.team_a:
            return PLAYER_A
        if color_name in self.team_b:
            return PLAYER_B
        return None

    def unpicked(self, all_colors=None):
        """The colours still on the table."""
        return [name for name in (all_colors or COLOR_POOL)
                if self.owner(name) is None]

    def in_play(self):
        """Every colour that has been chosen, Player A's first."""
        return self.team_a + self.team_b

    def next_picker(self):
        """Whose turn it is: the side with fewer colours, A first on a tie.

        Taking turns like this is what makes the pick feel fair when two
        players are standing at the booth together. It is also the only rule
        needed to keep the teams the same size - there is no counting code
        anywhere else.
        """
        if len(self.team_a) <= len(self.team_b) and len(self.team_a) < self.dice_count:
            return PLAYER_A
        if len(self.team_b) < self.dice_count:
            return PLAYER_B
        return None

    def take(self, color_name, player=None):
        """Give a free colour to a player. Returns True if it worked.

        With no player named it goes to whoever's turn it is. A colour that is
        already taken stays where it is, and a full team cannot take more.
        """
        if self.owner(color_name) is not None:
            return False
        player = player or self.next_picker()
        if player is None:
            return False
        team = self.colors(player)
        if len(team) >= self.dice_count:
            return False
        team.append(color_name)
        return True

    def drop(self, color_name):
        """Put a colour back on the table."""
        for team in (self.team_a, self.team_b):
            if color_name in team:
                team.remove(color_name)
                return True
        return False

    def tap(self, color_name):
        """One tap: take a free colour, or give back one you already own.

        This is what the screen calls, so a player who misclicks just taps
        again instead of hunting for an undo button.
        """
        if self.owner(color_name) is not None:
            self.drop(color_name)
            return None
        self.take(color_name)
        return self.owner(color_name)

    @property
    def teams_ready(self):
        """True once both sides have chosen all of their colours."""
        return (len(self.team_a) == self.dice_count
                and len(self.team_b) == self.dice_count)

    def auto_fill(self, all_colors=None, rng=None):
        """Deal the remaining colours out at random, alternating sides."""
        import random as _random
        shuffler = rng or _random
        left = self.unpicked(all_colors)
        shuffler.shuffle(left)
        for color_name in left:
            if self.next_picker() is None:
                break
            self.take(color_name)

    # ==================================================================== rules
    @staticmethod
    def total_for(results, colors):
        """Add up one team's three dice."""
        return sum(results[color] for color in colors)

    def judge(self, results):
        """Work out the winner from DiceSet.results().

        Returns a dictionary the result screen can display directly.
        """
        total_a = self.total_for(results, self.team_a)
        total_b = self.total_for(results, self.team_b)

        if total_a > total_b:
            winner = PLAYER_A
        elif total_b > total_a:
            winner = PLAYER_B
        else:
            winner = TIE

        if winner == TIE:
            self.rematches += 1
        else:
            self.wins[winner] += 1

        self.last_result = {
            "winner": winner,
            "total_a": total_a,
            "total_b": total_b,
            "difference": abs(total_a - total_b),
            "results": dict(results),
            "wins": dict(self.wins),
            "team_a": list(self.team_a),
            "team_b": list(self.team_b),
            "dice_count": self.dice_count,
        }
        return self.last_result

    # ================================================================== helpers
    def reset_score(self):
        self.wins = {PLAYER_A: 0, PLAYER_B: 0}
        self.rematches = 0
        self.last_result = None

    def colors_for(self, player):
        return self.colors(player)
