"""
Game engine: owns all Blackjack state and rules, plus the two things
that make it "Mafia" flavored — a dealer that sometimes cheats when it
would otherwise bust, and cosmetic NPC hands that eat into the shoe.
No UI code lives here — the GUI just calls these methods and reads the
results, which makes this layer independently testable.
"""

import random

from deck import Deck
from hand import Hand
import loan


class GameEngine:
    def __init__(self, starting_balance=500, loan_level=1):
        self.balance = starting_balance
        self.bet = 0
        self.deck = Deck()
        self.player_hand = Hand()
        self.dealer_hand = Hand()
        self.npc_hands = []
        self.dealer_hidden = True
        self.round_active = False
        self.dealer_cheated = False
        self.loan_level = loan_level

    def set_loan_level(self, loan_level):
        """Called by the GUI after loan.evaluate_round() changes the level,
        so the next round's difficulty reflects it."""
        self.loan_level = loan_level

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
        self.dealer_cheated = False

        npc_count = loan.npc_count_for_level(self.loan_level)
        self.npc_hands = [Hand() for _ in range(npc_count)]

        for _ in range(2):
            self.player_hand.add(self.deck.deal())
            self.dealer_hand.add(self.deck.deal())
            for npc_hand in self.npc_hands:
                npc_hand.add(self.deck.deal())

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

    def hit(self, insurance_active=False):
        self.player_hand.add(self.deck.deal())
        if self.player_hand.is_bust():
            self.dealer_hidden = False
            loss = self.bet // 2 if insurance_active else self.bet
            self.balance -= loss
            self._end_round()
            note = " (insurance halved the loss)" if insurance_active else ""
            return {"ok": True, "status": "round_over", "message": f"Bust! You lose ${loss}{note}"}
        return {"ok": True, "status": "in_progress", "message": None}

    def stand(self, cheat_blocked=False, insurance_active=False):
        self.dealer_hidden = False
        self._play_dealer_hand(cheat_blocked)

        pv, dv = self.player_hand.value(), self.dealer_hand.value()
        cheat_note = " The dealer swapped a card!" if self.dealer_cheated else ""

        if dv > 21 or pv > dv:
            self.balance += self.bet
            message = f"You win ${self.bet}! ({pv} vs {dv}){cheat_note}"
        elif pv == dv:
            message = f"Push ({pv} vs {dv}){cheat_note}"
        else:
            loss = self.bet // 2 if insurance_active else self.bet
            self.balance -= loss
            note = " (insurance halved the loss)" if insurance_active else ""
            message = f"Dealer wins ({dv} vs {pv}){cheat_note}{note}"

        self._end_round()
        return {"ok": True, "status": "round_over", "message": message}

    def _play_dealer_hand(self, cheat_blocked):
        """Dealer hits to 17+. At higher loan levels, a bust has a chance
        to be quietly reversed — the corrupt-casino flavor — unless the
        player blocked it with a Sharp Eyes item."""
        cheat_chance = 0 if cheat_blocked else loan.cheat_chance_for_level(self.loan_level)

        while self.dealer_hand.value() < 17:
            self.dealer_hand.add(self.deck.deal())
            if self.dealer_hand.is_bust() and random.random() < cheat_chance:
                self._attempt_cheat()

    def _attempt_cheat(self):
        """Swap the card that just caused a bust for a safer one, if one
        can be found within a few tries."""
        self.dealer_hand.cards.pop()
        for _ in range(10):
            candidate = self.deck.deal()
            self.dealer_hand.add(candidate)
            if not self.dealer_hand.is_bust():
                self.dealer_cheated = True
                return
            self.dealer_hand.cards.pop()
        # couldn't find a safe card — dealer just stays as they were before the pop
        self.dealer_hand.add(self.deck.deal())

    def peek_dealer_hole_card(self):
        """Used by the Peek shop item — reveals the hidden card early
        without ending the round."""
        self.dealer_hidden = False

    def _end_round(self):
        self.round_active = False
        self.bet = 0

    @property
    def is_game_over(self):
        return self.balance <= 0
