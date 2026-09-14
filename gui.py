"""Tkinter view layer. Holds no game rules — just draws state
from GameEngine and forwards button clicks to it."""

import tkinter as tk
from tkinter import font as tkfont

from engine import GameEngine
import constants as C


class BlackjackGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Blackjack")
        self.configure(bg=C.FELT_DARK)
        self.resizable(False, False)

        self.engine = GameEngine()

        self.card_font = tkfont.Font(family="Georgia", size=20, weight="bold")
        self.suit_font = tkfont.Font(size=28)
        self.label_font = tkfont.Font(family="Helvetica", size=13, weight="bold")
        self.status_font = tkfont.Font(family="Helvetica", size=16, weight="bold")

        self._build_layout()
        self._redraw()

    # ----- layout -----

    def _build_layout(self):
        top = tk.Frame(self, bg=C.FELT_DARK)
        top.pack(fill="x", padx=10, pady=(10, 0))

        self.balance_label = tk.Label(
            top, text="", font=self.label_font, bg=C.FELT_DARK, fg=C.GOLD
        )
        self.balance_label.pack(side="left")

        self.status_label = tk.Label(
            self, text="Place your bet to start", font=self.status_font,
            bg=C.FELT_DARK, fg=C.TEXT_LIGHT
        )
        self.status_label.pack(pady=(6, 0))

        self.canvas = tk.Canvas(
            self, width=C.CANVAS_WIDTH, height=C.CANVAS_HEIGHT, bg=C.FELT, highlightthickness=0
        )
        self.canvas.pack(padx=10, pady=10)

        controls = tk.Frame(self, bg=C.FELT_DARK)
        controls.pack(fill="x", padx=10, pady=(0, 10))

        bet_frame = tk.Frame(controls, bg=C.FELT_DARK)
        bet_frame.pack(side="left")
        for amount in C.BET_CHIPS:
            tk.Button(
                bet_frame, text=f"${amount}", width=6, font=self.label_font,
                bg=C.GOLD, fg="#1a1a1a", relief="flat",
                command=lambda a=amount: self._on_add_bet(a)
            ).pack(side="left", padx=3)

        tk.Button(
            bet_frame, text="Clear", width=6, font=self.label_font,
            bg="#8b1e1e", fg="white", relief="flat", command=self._on_clear_bet
        ).pack(side="left", padx=3)

        self.deal_btn = tk.Button(
            bet_frame, text="Deal", width=8, font=self.label_font,
            bg="#1e5f2e", fg="white", relief="flat", command=self._on_deal
        )
        self.deal_btn.pack(side="left", padx=(15, 3))

        action_frame = tk.Frame(controls, bg=C.FELT_DARK)
        action_frame.pack(side="right")

        self.hit_btn = tk.Button(
            action_frame, text="Hit", width=8, font=self.label_font,
            bg="#2a4d8f", fg="white", relief="flat", state="disabled",
            command=self._on_hit
        )
        self.hit_btn.pack(side="left", padx=3)

        self.stand_btn = tk.Button(
            action_frame, text="Stand", width=8, font=self.label_font,
            bg="#2a4d8f", fg="white", relief="flat", state="disabled",
            command=self._on_stand
        )
        self.stand_btn.pack(side="left", padx=3)

    # ----- drawing -----

    def _draw_card(self, x, y, card, face_up=True):
        w, h = C.CARD_WIDTH, C.CARD_HEIGHT
        if face_up:
            self.canvas.create_rectangle(x, y, x + w, y + h, fill="white", outline="#333", width=2)
            color = "#c0392b" if card.is_red else "#111"
            self.canvas.create_text(x + 12, y + 16, text=card.rank, font=self.card_font, fill=color, anchor="w")
            self.canvas.create_text(x + w / 2, y + h / 2 + 8, text=card.suit, font=self.suit_font, fill=color)
        else:
            self.canvas.create_rectangle(x, y, x + w, y + h, fill=C.CARD_BACK, outline="#333", width=2)
            self.canvas.create_rectangle(x + 8, y + 8, x + w - 8, y + h - 8, outline=C.GOLD, width=2)

    def _redraw(self):
        e = self.engine
        self.canvas.delete("all")

        self.canvas.create_text(15, 15, text="Dealer", font=self.label_font, fill=C.TEXT_LIGHT, anchor="nw")
        for i, card in enumerate(e.dealer_hand.cards):
            face_up = not (e.dealer_hidden and i == 0)
            self._draw_card(15 + i * 95, 40, card, face_up=face_up)

        self.canvas.create_text(15, 260, text="You", font=self.label_font, fill=C.TEXT_LIGHT, anchor="nw")
        for i, card in enumerate(e.player_hand.cards):
            self._draw_card(15 + i * 95, 285, card, face_up=True)

        if not e.dealer_hidden and e.dealer_hand.cards:
            self.canvas.create_text(700, 55, text=str(e.dealer_hand.value()), font=self.status_font, fill=C.GOLD)
        if e.player_hand.cards:
            self.canvas.create_text(700, 300, text=str(e.player_hand.value()), font=self.status_font, fill=C.GOLD)

        self.balance_label.config(text=f"Balance: ${e.balance}  |  Bet: ${e.bet}")

    def _set_status(self, text):
        if text:
            self.status_label.config(text=text)

    # ----- button handlers (thin wrappers over the engine) -----

    def _on_add_bet(self, amount):
        ok, message = self.engine.add_bet(amount)
        self._redraw()
        self._set_status(message or f"Bet: ${self.engine.bet} — press Deal when ready")

    def _on_clear_bet(self):
        ok, message = self.engine.clear_bet()
        self._redraw()
        self._set_status(message or "Place your bet to start")

    def _on_deal(self):
        result = self.engine.deal()
        self._redraw()
        self._set_status(result["message"])
        if not result["ok"]:
            return
        if result["status"] == "in_progress":
            self.hit_btn.config(state="normal")
            self.stand_btn.config(state="normal")
        else:
            self._after_round()

    def _on_hit(self):
        result = self.engine.hit()
        self._redraw()
        if result["status"] == "round_over":
            self._set_status(result["message"])
            self._after_round()

    def _on_stand(self):
        result = self.engine.stand()
        self._redraw()
        self._set_status(result["message"])
        self._after_round()

    def _after_round(self):
        self.hit_btn.config(state="disabled")
        self.stand_btn.config(state="disabled")
        if self.engine.is_game_over:
            self.status_label.config(text="Out of chips — game over")
            self.deal_btn.config(state="disabled")
