"""
game/history.py
---------------
Keeps a short memory of what has happened at the booth.

Two separate things live here:

  RoundHistory   the last few rounds, so the strip along the bottom of the
                 screen can show them. Real perya boards do exactly this and
                 players love watching for patterns in it.

  Streaks        how many rounds in a row the player has won or lost, plus a
                 few totals for the session.

Like betting.py this file has no drawing code, so it can be tested on its own.

A warning worth understanding, and a good thing to say if a panelist asks:
the history strip does NOT help anyone predict the next roll. Every roll uses
a fresh random number and knows nothing about the last one. Believing
otherwise is called the gambler's fallacy. The strip is there because it is
fun to look at, not because it means anything.
"""

MAX_ENTRIES = 12


class RoundHistory:
    """The last MAX_ENTRIES rounds, newest last."""

    def __init__(self, limit=MAX_ENTRIES):
        self.limit = limit
        self.entries = []

    def add(self, color, number, won):
        """Record one finished round."""
        self.entries.append({"color": color, "number": number, "won": bool(won)})
        # keep the list short: drop the oldest once it is full
        if len(self.entries) > self.limit:
            self.entries.pop(0)

    def recent(self, count=None):
        """The newest entries, oldest first, ready to draw left to right."""
        if count is None:
            return list(self.entries)
        return self.entries[-count:]

    def clear(self):
        self.entries.clear()


class Streaks:
    """Wins and losses in a row, plus session totals."""

    def __init__(self):
        self.current = 0        # positive = wins in a row, negative = losses
        self.best_win_streak = 0
        self.worst_loss_streak = 0
        self.rounds = 0
        self.wins = 0
        self.biggest_win = 0

    def record(self, won, payout=0):
        self.rounds += 1

        if won:
            self.wins += 1
            self.current = self.current + 1 if self.current > 0 else 1
            self.best_win_streak = max(self.best_win_streak, self.current)
            self.biggest_win = max(self.biggest_win, payout)
        else:
            self.current = self.current - 1 if self.current < 0 else -1
            self.worst_loss_streak = min(self.worst_loss_streak, self.current)

    # ------------------------------------------------------------- readouts
    def label(self):
        """A short string for the corner of the screen."""
        if self.current == 0:
            return "NO STREAK"
        if self.current > 0:
            return f"{self.current} WIN{'S' if self.current > 1 else ''} IN A ROW"
        losses = -self.current
        return f"{losses} LOSS{'ES' if losses > 1 else ''} IN A ROW"

    def win_rate(self):
        """Percentage of rounds won so far, as a whole number."""
        if self.rounds == 0:
            return 0
        return round(self.wins * 100 / self.rounds)

    def reset(self):
        self.__init__()
