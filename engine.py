"""
Game engine: owns all Blackjack state and rules.
No UI code lives here — the GUI just calls these methods and
reads the results, which makes this layer independently testable
and swappable (Tkinter today, something else tomorrow).
"""

from deck import Deck
from hand import Hand


class GameEngine:
    def __init__(self, starting_balance=500):
        self.balance = starting_balance
        self.bet = 0
        self.deck = Deck()
        self.player_hand = Hand()
        self.dealer_hand = Hand()
        self.dealer_hidden = True
        self.round_active = False

    # ----- betting (only allowed between rounds) -----

    def add_bet(self, amount):
        if self.round_active:
            return False, "Round already in progress"
        if self.bet + amount > self.balance:
            return False, "Not enough balance for that bet"
        self.bet += amount
        return True, None

    def clear_bet(self):
        if self.round_active:
            return False, "Round already in progress"
        self.bet = 0
        return True, None

    # ----- round flow -----

    def deal(self):
        if self.bet <= 0:
            return {"ok": False, "message": "Place a bet first"}

        self.player_hand = Hand()
        self.dealer_hand = Hand()
        self.dealer_hidden = True
        for _ in range(2):
            self.player_hand.add(self.deck.deal())
            self.dealer_hand.add(self.deck.deal())
        self.round_active = True

        if self.player_hand.is_blackjack() or self.dealer_hand.is_blackjack():
            return self._resolve_naturals()

        return {"ok": True, "status": "in_progress", "message": "Hit or Stand?"}

    def _resolve_naturals(self):
        self.dealer_hidden = False
        player_bj = self.player_hand.is_blackjack()
        dealer_bj = self.dealer_hand.is_blackjack()

        if player_bj and dealer_bj:
            message = "Both blackjack — push"
        elif player_bj:
            winnings = int(self.bet * 1.5)
            self.balance += winnings
            message = f"Blackjack! You win ${winnings}"
        else:
            self.balance -= self.bet
            message = "Dealer has blackjack — you lose"

        self._end_round()
        return {"ok": True, "status": "round_over", "message": message}

    def hit(self):
        self.player_hand.add(self.deck.deal())
        if self.player_hand.is_bust():
            self.dealer_hidden = False
            self.balance -= self.bet
            self._end_round()
            return {"ok": True, "status": "round_over", "message": f"Bust! You lose ${self.bet}"}
        return {"ok": True, "status": "in_progress", "message": None}

    def stand(self):
        self.dealer_hidden = False
        while self.dealer_hand.value() < 17:
            self.dealer_hand.add(self.deck.deal())

        pv, dv = self.player_hand.value(), self.dealer_hand.value()
        if dv > 21 or pv > dv:
            self.balance += self.bet
            message = f"You win ${self.bet}! ({pv} vs {dv})"
        elif pv == dv:
            message = f"Push ({pv} vs {dv})"
        else:
            self.balance -= self.bet
            message = f"Dealer wins ({dv} vs {pv})"

        self._end_round()
        return {"ok": True, "status": "round_over", "message": message}

    def _end_round(self):
        self.round_active = False
        self.bet = 0

    @property
    def is_game_over(self):
        return self.balance <= 0
