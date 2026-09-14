"""A single playing card."""

RED_SUITS = {"♥", "♦"}


class Card:
    def __init__(self, suit, rank, value):
        self.suit = suit
        self.rank = rank
        self.value = value

    @property
    def is_red(self):
        return self.suit in RED_SUITS

    def __repr__(self):
        return f"{self.rank}{self.suit}"
