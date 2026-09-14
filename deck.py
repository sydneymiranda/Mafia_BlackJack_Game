"""A shuffled multi-deck shoe."""

import random

from card import Card

SUITS = ["♠", "♥", "♦", "♣"]
RANKS = [
    ("A", 11), ("2", 2), ("3", 3), ("4", 4), ("5", 5), ("6", 6),
    ("7", 7), ("8", 8), ("9", 9), ("10", 10), ("J", 10), ("Q", 10), ("K", 10),
]


class Deck:
    def __init__(self, num_decks=4):
        self.num_decks = num_decks
        self.cards = []
        self._build()

    def _build(self):
        self.cards = [
            Card(suit, rank, value)
            for _ in range(self.num_decks)
            for suit in SUITS
            for rank, value in RANKS
        ]
        random.shuffle(self.cards)

    def deal(self):
        if len(self.cards) < 15:
            self._build()
        return self.cards.pop()
