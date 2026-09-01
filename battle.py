"""
game/battle.py
--------------
BATTLE ROYALE: last player standing.

Consequence Pool finds a LOSER in one round. This finds a WINNER over several:

    every round, all the surviving players roll
    the lowest roll is knocked out
    repeat until one player is left

Ties for lowest go to sudden death between just those players, exactly like
Consequence Pool - and that logic is reused rather than rewritten, which is
why this file is short.

Free play: no credits, no betting. It is the mode for a crowd.
"""

from config import settings
from game.consequences import lowest_rollers


class BattleRoyale:
    """Who is still in, who just went out, and who won."""

    def __init__(self, player_count=4):
        self.player_count = 0
        self.alive = []
        self.knocked_out = []       # in the order they went out
        self.round_number = 0
        self.winner = None
        self.set_players(player_count)

    # ================================================================== setup
    def set_players(self, count):
        """Start a fresh battle with this many players."""
        count = max(2, min(settings.MAX_PLAYERS, int(count)))
        self.player_count = count
        self.alive = settings.COLOR_ORDER[:count]
        self.knocked_out = []
        self.round_number = 0
        self.winner = None

    def restart(self):
        self.set_players(self.player_count)

    # ================================================================= rounds
    @property
    def finished(self):
        return self.winner is not None

    def lowest(self, results, among=None):
        """Who rolled lowest among the players still in.

        Returns a list: more than one name means a tie that has to be settled
        by a reroll between just those players.
        """
        return lowest_rollers(results, among or self.alive)

    def knock_out(self, color_name):
        """Remove a player. If one is left, they win."""
        if color_name in self.alive:
            self.alive.remove(color_name)
            self.knocked_out.append(color_name)

        if len(self.alive) == 1:
            self.winner = self.alive[0]
        return self.winner

    def begin_round(self):
        self.round_number += 1
        return list(self.alive)

    def placement(self, color_name):
        """What position a player finished in. 1 is the winner."""
        if color_name == self.winner:
            return 1
        if color_name in self.knocked_out:
            # knocked out first = last place
            return self.player_count - self.knocked_out.index(color_name)
        return None
