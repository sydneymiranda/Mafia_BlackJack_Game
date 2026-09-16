"""Tkinter table view. Holds no game rules — draws state from GameEngine
and forwards clicks to it and to loan.py for boss/target progress."""

import tkinter as tk
from tkinter import font as tkfont

from base_window import BaseGameWindow
from engine import GameEngine
import constants as C
import database
import loan


class BlackjackGUI(BaseGameWindow):
    def __init__(self, user_id, start_fullscreen=False):
        super().__init__("Mafia Blackjack — At the Table", start_fullscreen=start_fullscreen)
        self.configure(bg=C.FELT_DARK)
        self.resizable(False, False)

        self.user_id = user_id
        starting_balance = database.get_balance(user_id)
        loan_state = database.get_loan_state(user_id)
        self.loan_state = loan_state
        self.engine = GameEngine(starting_balance=starting_balance, loan_level=loan_state["loan_level"])
        self.go_home = False  # main.py checks this after mainloop exits
        self.active_items = {"peek": False, "sharp_eyes": False, "insurance": False}

        self.card_font = tkfont.Font(family="Georgia", size=20, weight="bold")
        self.suit_font = tkfont.Font(size=28)
        self.small_font = tkfont.Font(size=16)
        self.label_font = tkfont.Font(family="Helvetica", size=13, weight="bold")
        self.status_font = tkfont.Font(family="Helvetica", size=15, weight="bold")

        self._build_window_controls()
        self._build_layout()
        self._redraw()
        self._finish_setup()

    def _build_window_controls(self):
        self._bind_fullscreen_keys()

    def _on_menu_click(self):
        database.set_balance(self.user_id, self.engine.balance)
        self.go_home = True
        self.destroy()

    # ----- layout -----

    def _build_layout(self):
        top = tk.Frame(self, bg=C.FELT_DARK)
        top.pack(fill="x", padx=10, pady=(10, 0))

        tk.Button(
            top, text="☰ Menu", font=self.label_font, bg="#333333", fg="white",
            relief="flat", command=self._on_menu_click
        ).pack(side="left")

        self.balance_label = tk.Label(
            top, text="", font=self.label_font, bg=C.FELT_DARK, fg=C.GOLD
        )
        self.balance_label.pack(side="right", padx=(0, 10))
        tk.Button(
            top, text="🗕", font=self.label_font, bg="#333333", fg="white",
            relief="flat", width=3, command=self.iconify
        ).pack(side="right", padx=4)
        tk.Button(
            top, text="⛶", font=self.label_font, bg="#333333", fg="white",
            relief="flat", width=3, command=self._toggle_fullscreen
        ).pack(side="right", padx=4)

        self.loan_label = tk.Label(
            self, text="", font=self.label_font, bg=C.FELT_DARK, fg="#e0a020"
        )
        self.loan_label.pack(pady=(6, 0))

        self.status_label = tk.Label(
            self, text="Place your bet to start", font=self.status_font,
            bg=C.FELT_DARK, fg=C.TEXT_LIGHT
        )
        self.status_label.pack(pady=(2, 0))

        self.canvas = tk.Canvas(
            self, width=C.CANVAS_WIDTH, height=C.CANVAS_HEIGHT, bg=C.FELT, highlightthickness=0
        )
        self.canvas.pack(padx=10, pady=10)

        # ----- shop item bar -----
        self.item_frame = tk.Frame(self, bg=C.FELT_DARK)
        self.item_frame.pack(fill="x", padx=10)
        self.item_buttons = {}
        for item_id, item in loan.SHOP_ITEMS.items():
            btn = tk.Button(
                self.item_frame, text=item["name"], font=self.label_font,
                bg="#4a3b1e", fg="white", relief="flat",
                command=lambda i=item_id: self._on_use_item(i)
            )
            btn.pack(side="left", padx=3, pady=4)
            self.item_buttons[item_id] = btn

        # ----- betting / action controls -----
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

        # ----- "run over" overlay controls (hidden until needed) -----
        self.continue_btn = tk.Button(
            self, text="Continue", font=self.label_font, width=16,
            bg="#1e5f2e", fg="white", relief="flat", command=self._on_continue_click
        )

    # ----- drawing -----

    def _draw_card(self, x, y, card, face_up=True, scale=1.0):
        w, h = C.CARD_WIDTH * scale, C.CARD_HEIGHT * scale
        if face_up:
            self.canvas.create_rectangle(x, y, x + w, y + h, fill="white", outline="#333", width=2)
            color = "#c0392b" if card.is_red else "#111"
            self.canvas.create_text(x + 10, y + 14 * scale, text=card.rank, font=self.card_font, fill=color, anchor="w")
            self.canvas.create_text(x + w / 2, y + h / 2 + 6, text=card.suit, font=self.suit_font, fill=color)
        else:
            self.canvas.create_rectangle(x, y, x + w, y + h, fill=C.CARD_BACK, outline="#333", width=2)
            self.canvas.create_rectangle(x + 6, y + 6, x + w - 6, y + h - 6, outline=C.GOLD, width=2)

    def _redraw(self):
        e = self.engine
        self.canvas.delete("all")

        self.canvas.create_text(15, 15, text="Dealer", font=self.label_font, fill=C.TEXT_LIGHT, anchor="nw")
        for i, card in enumerate(e.dealer_hand.cards):
            face_up = not (e.dealer_hidden and i == 0)
            self._draw_card(15 + i * 95, 40, card, face_up=face_up)

        # NPC hands — cosmetic, card backs only, shown along the top-right
        for n, npc_hand in enumerate(e.npc_hands):
            nx = 480 + n * 90
            self.canvas.create_text(nx, 15, text=f"NPC {n + 1}", font=self.small_font, fill="#9aa", anchor="nw")
            for i, card in enumerate(npc_hand.cards):
                self._draw_card(nx + i * 20, 40, card, face_up=False, scale=0.55)

        self.canvas.create_text(15, 260, text="You", font=self.label_font, fill=C.TEXT_LIGHT, anchor="nw")
        for i, card in enumerate(e.player_hand.cards):
            self._draw_card(15 + i * 95, 285, card, face_up=True)

        if not e.dealer_hidden and e.dealer_hand.cards:
            self.canvas.create_text(700, 55, text=str(e.dealer_hand.value()), font=self.status_font, fill=C.GOLD)
        if e.player_hand.cards:
            self.canvas.create_text(700, 300, text=str(e.player_hand.value()), font=self.status_font, fill=C.GOLD)

        self.balance_label.config(text=f"Balance: ${e.balance}  |  Bet: ${e.bet}")
        self.loan_label.config(
            text=f"Boss level {self.loan_state['loan_level']} — need ${self.loan_state['target']} "
                 f"within {self.loan_state['rounds_left']} round(s)"
        )
        self._refresh_item_buttons()

    def _refresh_item_buttons(self):
        inventory = database.get_inventory(self.user_id)
        for item_id, btn in self.item_buttons.items():
            count = inventory.get(item_id, 0)
            already_used = self.active_items.get(item_id, False)
            btn.config(text=f"{loan.SHOP_ITEMS[item_id]['name']} ({count})")
            can_use = count > 0 and not already_used and self.engine.round_active
            btn.config(state="normal" if can_use else "disabled")

    def _set_status(self, text):
        if text:
            self.status_label.config(text=text)

    # ----- shop item usage (mid-round) -----

    def _on_use_item(self, item_id):
        if self.active_items.get(item_id):
            return
        if not database.use_item(self.user_id, item_id):
            return
        self.active_items[item_id] = True
        if item_id == "peek":
            self.engine.peek_dealer_hole_card()
            self._set_status("You peek at the dealer's hidden card.")
        elif item_id == "sharp_eyes":
            self._set_status("You're watching the dealer closely this round.")
        elif item_id == "insurance":
            self._set_status("Insurance is active for this round.")
        self._redraw()

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
        self.active_items = {k: False for k in self.active_items}
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
        result = self.engine.hit(insurance_active=self.active_items["insurance"])
        self._redraw()
        if result["status"] == "round_over":
            self._set_status(result["message"])
            self._after_round()

    def _on_stand(self):
        result = self.engine.stand(
            cheat_blocked=self.active_items["sharp_eyes"],
            insurance_active=self.active_items["insurance"],
        )
        self._redraw()
        self._set_status(result["message"])
        self._after_round()

    def _after_round(self):
        self.hit_btn.config(state="disabled")
        self.stand_btn.config(state="disabled")
        database.set_balance(self.user_id, self.engine.balance)

        loan_result = loan.evaluate_round(self.user_id, self.engine.balance)
        self.loan_state = database.get_loan_state(self.user_id)
        self.engine.set_loan_level(self.loan_state["loan_level"])
        self._redraw()

        if loan_result["event"] in ("success", "failed"):
            self.loan_state = database.get_loan_state(self.user_id)
            self.engine.balance = database.get_balance(self.user_id)
            self._redraw()
            self._show_run_over(loan_result["message"])
        else:
            self.status_label.config(text=self.status_label.cget("text") + "  —  " + loan_result["message"])
            if self.engine.is_game_over:
                self.status_label.config(text="Out of chips — the boss will hear about this.")
                self.deal_btn.config(state="disabled")

    def _show_run_over(self, message):
        self.deal_btn.config(state="disabled")
        for btn in self.item_buttons.values():
            btn.config(state="disabled")
        self.status_label.config(text=message)
        self.continue_btn.pack(pady=(0, 10))

    def _on_continue_click(self):
        self._on_menu_click()