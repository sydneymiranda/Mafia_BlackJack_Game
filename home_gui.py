"""
Home hub: house / shop / car. This is the screen between login and the
table — shows your boss's loan status and lets you go to the Shop or
get in the car to play. Same responsive-canvas approach as login_gui.py
so fullscreen works correctly here too.
"""

import os
import tkinter as tk
from tkinter import font as tkfont

from base_window import BaseGameWindow
import auth
import database

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

BG_IMAGE_PATH = "assets/home_background.png"  # drop your art here later


class HomeScreen(BaseGameWindow):
    def __init__(self, user_id, start_fullscreen=False):
        super().__init__("Mafia Blackjack — Home", start_fullscreen=start_fullscreen)
        self.geometry("900x600")

        self.user_id = user_id
        self.next_action = None  # "shop" | "play" | "logout", read by main.py

        self._bg_pil = None
        self._bg_photo = None
        self._bg_image_id = None

        if PIL_AVAILABLE and os.path.exists(BG_IMAGE_PATH):
            self._bg_pil = Image.open(BG_IMAGE_PATH)

        self.title_font = tkfont.Font(family="Georgia", size=28, weight="bold")
        self.sub_font = tkfont.Font(family="Helvetica", size=13)
        self.btn_font = tkfont.Font(family="Helvetica", size=13, weight="bold")

        self._build_window_controls()
        self._build_canvas()
        self._refresh_status()
        self._finish_setup()

    # ----- window chrome -----

    def _build_window_controls(self):
        bar = tk.Frame(self, bg="#0d0d0d")
        bar.pack(side="top", fill="x")
        tk.Button(
            bar, text="🗕", font=self.btn_font, bg="#0d0d0d", fg="#e0e0e0",
            bd=0, activebackground="#222", command=self.iconify
        ).pack(side="right", padx=(0, 4), pady=4)
        tk.Button(
            bar, text="⛶", font=self.btn_font, bg="#0d0d0d", fg="#e0e0e0",
            bd=0, activebackground="#222", command=self._toggle_fullscreen
        ).pack(side="right", padx=4, pady=4)
        tk.Button(
            bar, text="Log out", font=self.btn_font, bg="#0d0d0d", fg="#e0a0a0",
            bd=0, activebackground="#222", command=self._on_logout
        ).pack(side="left", padx=4, pady=4)
        self._bind_fullscreen_keys()

    def _on_logout(self):
        auth.clear_session()
        self.next_action = "logout"
        self.destroy()

    # ----- responsive canvas -----

    def _build_canvas(self):
        self.canvas = tk.Canvas(self, bg="#0d0d0d", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.bg_rect_id = self.canvas.create_rectangle(0, 0, 1, 1, fill="#141414", outline="")
        self.accent_rect_id = self.canvas.create_rectangle(0, 0, 1, 1, fill="#0b5d2e", outline="")
        self.title_id = self.canvas.create_text(0, 0, text="MAFIA BLACKJACK", font=self.title_font, fill="#d4af37")
        self.status_id = self.canvas.create_text(0, 0, text="", font=self.sub_font, fill="#e0e0e0")

        self.button_frame = tk.Frame(self.canvas, bg="#141414")
        self.button_window = self.canvas.create_window(0, 0, window=self.button_frame, anchor="n")

        self._build_buttons()

        self.canvas.bind("<Configure>", self._on_resize)

    def _build_buttons(self):
        tk.Button(
            self.button_frame, text="🏚 The House", font=self.btn_font, width=26,
            bg="#222222", fg="#999999", relief="flat", command=self._on_house_click
        ).pack(pady=6)
        tk.Button(
            self.button_frame, text="🛒 Visit the Shop", font=self.btn_font, width=26,
            bg="#2a4d8f", fg="white", relief="flat", command=self._on_shop_click
        ).pack(pady=6)
        tk.Button(
            self.button_frame, text="🚗 Get in the Car — Play", font=self.btn_font, width=26,
            bg="#8b1e1e", fg="white", relief="flat", command=self._on_play_click
        ).pack(pady=6)

    def _on_resize(self, event):
        width, height = event.width, event.height
        if width < 10 or height < 10:
            return

        self.canvas.coords(self.bg_rect_id, 0, 0, width, height)
        self.canvas.coords(self.accent_rect_id, 0, height * 0.7, width, height)

        if self._bg_pil is not None:
            self._bg_photo = self._make_cover_image(width, height)
            if self._bg_image_id is None:
                self._bg_image_id = self.canvas.create_image(0, 0, anchor="nw", image=self._bg_photo)
                self.canvas.tag_lower(self._bg_image_id)
            else:
                self.canvas.itemconfig(self._bg_image_id, image=self._bg_photo)
                self.canvas.coords(self._bg_image_id, 0, 0)

        self.canvas.coords(self.title_id, width / 2, height * 0.14)
        self.canvas.coords(self.status_id, width / 2, height * 0.22)
        self.canvas.coords(self.button_window, width / 2, height * 0.32)

    def _make_cover_image(self, width, height):
        img = self._bg_pil
        img_ratio = img.width / img.height
        target_ratio = width / height
        if img_ratio > target_ratio:
            new_height, new_width = height, int(height * img_ratio)
        else:
            new_width, new_height = width, int(width / img_ratio)
        resized = img.resize((max(new_width, 1), max(new_height, 1)))
        left = (new_width - width) // 2
        top = (new_height - height) // 2
        cropped = resized.crop((left, top, left + width, top + height))
        return ImageTk.PhotoImage(cropped)

    # ----- content -----

    def _refresh_status(self):
        loan_state = database.get_loan_state(self.user_id)
        balance = database.get_balance(self.user_id)
        self.canvas.itemconfig(
            self.status_id,
            text=(
                f"Balance: ${balance}   |   Boss level {loan_state['loan_level']}"
                f"   |   Need ${loan_state['target']} within {loan_state['rounds_left']} round(s)"
            ),
        )

    def _on_house_click(self):
        self.canvas.itemconfig(self.status_id, text="Nothing to do here yet — more coming later.")
        self.after(2000, self._refresh_status)

    def _on_shop_click(self):
        self.next_action = "shop"
        self.destroy()

    def _on_play_click(self):
        self.next_action = "play"
        self.destroy()
