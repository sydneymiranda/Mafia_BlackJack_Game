"""Shop screen — buy items that counter the dealer's cheats and the
boss's escalating targets. Straightforward fixed layout (no responsive
canvas needed here since it's just a list)."""

import tkinter as tk
from tkinter import font as tkfont

from base_window import BaseGameWindow
import constants as C
import database
import loan


class ShopScreen(BaseGameWindow):
    def __init__(self, user_id, start_fullscreen=False):
        super().__init__("Mafia Blackjack — Shop", start_fullscreen=start_fullscreen)
        self.geometry("640x520")
        self.configure(bg="#141414")

        self.user_id = user_id

        self.title_font = tkfont.Font(family="Georgia", size=24, weight="bold")
        self.label_font = tkfont.Font(family="Helvetica", size=13, weight="bold")
        self.desc_font = tkfont.Font(family="Helvetica", size=11)

        self._build_window_controls()
        self._build_layout()
        self._refresh()
        self._finish_setup()

    def _build_window_controls(self):
        bar = tk.Frame(self, bg="#141414")
        bar.pack(side="top", fill="x")
        tk.Button(
            bar, text="🗕", font=self.label_font, bg="#141414", fg="#e0e0e0",
            bd=0, command=self.iconify
        ).pack(side="right", padx=(0, 4), pady=4)
        tk.Button(
            bar, text="⛶", font=self.label_font, bg="#141414", fg="#e0e0e0",
            bd=0, command=self._toggle_fullscreen
        ).pack(side="right", padx=4, pady=4)
        tk.Button(
            bar, text="← Back", font=self.label_font, bg="#141414", fg="#e0e0e0",
            bd=0, command=self._on_back
        ).pack(side="left", padx=4, pady=4)
        self._bind_fullscreen_keys()

    def _on_back(self):
        self.destroy()

    def _build_layout(self):
        tk.Label(
            self, text="THE SHOP", font=self.title_font, bg="#141414", fg="#d4af37"
        ).pack(pady=(10, 0))

        self.balance_label = tk.Label(
            self, text="", font=self.label_font, bg="#141414", fg=C.GOLD
        )
        self.balance_label.pack(pady=(2, 10))

        self.items_frame = tk.Frame(self, bg="#141414")
        self.items_frame.pack(fill="both", expand=True, padx=20)

        self.status_label = tk.Label(
            self, text="", font=self.label_font, bg="#141414", fg="#e0a0a0"
        )
        self.status_label.pack(pady=(0, 10))

    def _refresh(self):
        for widget in self.items_frame.winfo_children():
            widget.destroy()

        balance = database.get_balance(self.user_id)
        inventory = database.get_inventory(self.user_id)
        self.balance_label.config(text=f"Balance: ${balance}")

        for item_id, item in loan.SHOP_ITEMS.items():
            row = tk.Frame(self.items_frame, bg="#1e1e1e")
            row.pack(fill="x", pady=6)

            text_col = tk.Frame(row, bg="#1e1e1e")
            text_col.pack(side="left", fill="x", expand=True, padx=10, pady=8)
            tk.Label(
                text_col, text=f"{item['name']}  —  ${item['price']}  (owned: {inventory.get(item_id, 0)})",
                font=self.label_font, bg="#1e1e1e", fg="white", anchor="w"
            ).pack(fill="x")
            tk.Label(
                text_col, text=item["desc"], font=self.desc_font, bg="#1e1e1e", fg="#aaaaaa",
                anchor="w", wraplength=380, justify="left"
            ).pack(fill="x")

            tk.Button(
                row, text="Buy", font=self.label_font, width=8,
                bg="#1e5f2e", fg="white", relief="flat",
                command=lambda i=item_id: self._on_buy(i)
            ).pack(side="right", padx=10)

    def _on_buy(self, item_id):
        ok, message = loan.buy_item(self.user_id, item_id)
        self.status_label.config(text=message)
        self._refresh()
