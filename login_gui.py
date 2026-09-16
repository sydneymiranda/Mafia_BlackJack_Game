"""
Start screen: mafia-themed title screen with Sign in with Google / Email /
Guest. Layout is fully responsive — it redraws on every resize, so
fullscreen and windowed both look correct.

If assets/mafia_background.png exists (with Pillow installed), that
image is scaled to cover the window. Otherwise a noir-casino background
is generated procedurally (gradient glow, poker-chip/diamond watermarks,
an art-deco gold border) so the screen still looks designed with zero
external assets.
"""

import os
import queue
import random
import threading
import tkinter as tk
from tkinter import font as tkfont

from base_window import BaseGameWindow
import auth
import database

try:
    from PIL import Image, ImageDraw, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

BG_IMAGE_PATH = "assets/mafia_background.png"  # drop your own art here later

GOLD = "#d4af37"
GOLD_DIM = "#8a6d24"
CARD_BG = "#111318"


def _lighten(hex_color, factor=1.18):
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    r, g, b = (min(255, int(c * factor)) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def _generate_noir_background(width=1600, height=1000):
    """Procedural fallback art: warm glow, scattered chip/diamond
    watermarks, art-deco gold border. All vector drawing, so it's fast
    even at large sizes — generated once and cached."""
    img = Image.new("RGB", (width, height), (5, 5, 5))
    draw = ImageDraw.Draw(img)

    cx, cy = width * 0.5, height * 0.32
    max_r = int((width ** 2 + height ** 2) ** 0.5 * 0.55)
    rings = 50
    for i in range(rings, 0, -1):
        t = i / rings
        r = int(max_r * t)
        shade = int(22 * (1 - t))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(shade + 8, shade // 2, shade // 2))

    rng = random.Random(7)
    for _ in range(14):
        r = rng.randint(30, 70)
        x = rng.randint(-r, width + r)
        y = rng.randint(-r, height + r)
        for ring in range(3):
            rr = r - ring * (r // 3)
            shade = 14 + ring * 4
            draw.ellipse([x - rr, y - rr, x + rr, y + rr], outline=(shade, shade, shade), width=2)

    for _ in range(10):
        s = rng.randint(20, 50)
        x = rng.randint(0, width)
        y = rng.randint(0, height)
        shade = rng.randint(10, 18)
        draw.polygon([(x, y - s), (x + s, y), (x, y + s), (x - s, y)], outline=(shade, shade, shade))

    m1, m2 = 22, 34
    gold, gold_dim = (150, 115, 45), (95, 72, 30)
    draw.rectangle([m1, m1, width - m1, height - m1], outline=gold, width=3)
    draw.rectangle([m2, m2, width - m2, height - m2], outline=gold_dim, width=1)
    d = 12
    for (cx2, cy2) in [(m1, m1), (width - m1, m1), (m1, height - m1), (width - m1, height - m1)]:
        draw.polygon([(cx2, cy2 - d), (cx2 + d, cy2), (cx2, cy2 + d), (cx2 - d, cy2)], fill=gold)

    return img


class LoginScreen(BaseGameWindow):
    def __init__(self, start_fullscreen=False):
        super().__init__("Mafia Blackjack", start_fullscreen=start_fullscreen)
        self.geometry("1000x650")

        self.result_queue = queue.Queue()
        self.user_id = None  # set on success, read by main.py after mainloop exits
        self._bg_pil = None
        self._bg_photo = None
        self._bg_image_id = None

        if PIL_AVAILABLE:
            if os.path.exists(BG_IMAGE_PATH):
                self._bg_pil = Image.open(BG_IMAGE_PATH)
            else:
                self._bg_pil = _generate_noir_background()

        self.title_font = tkfont.Font(family="Georgia", size=44, weight="bold")
        self.sub_font = tkfont.Font(family="Georgia", size=14, slant="italic")
        self.btn_font = tkfont.Font(family="Helvetica", size=13, weight="bold")

        self._build_window_controls()
        self._build_canvas()
        self._show_login_buttons()
        self._try_auto_login()
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
        self._bind_fullscreen_keys()

    # ----- responsive canvas -----

    def _build_canvas(self):
        self.canvas = tk.Canvas(self, bg="#0d0d0d", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.bg_rect_id = self.canvas.create_rectangle(0, 0, 1, 1, fill="#050505", outline="")

        # title with a drop shadow (shadow drawn first, sits underneath)
        self.title_shadow_id = self.canvas.create_text(
            0, 0, text="MAFIA BLACKJACK", font=self.title_font, fill="#000000"
        )
        self.title_id = self.canvas.create_text(
            0, 0, text="MAFIA BLACKJACK", font=self.title_font, fill=GOLD
        )
        self.subtitle_id = self.canvas.create_text(
            0, 0, text="the house always has a cut", font=self.sub_font, fill="#cfcfcf"
        )

        # small decorative divider: line - diamond - line
        self.divider_left_id = self.canvas.create_line(0, 0, 0, 0, fill=GOLD_DIM, width=2)
        self.divider_diamond_id = self.canvas.create_polygon(0, 0, 0, 0, 0, 0, 0, 0, fill=GOLD)
        self.divider_right_id = self.canvas.create_line(0, 0, 0, 0, fill=GOLD_DIM, width=2)

        self.status_text_id = self.canvas.create_text(0, 0, text="", font=self.btn_font, fill="#e0e0e0")

        self.button_frame = tk.Frame(self.canvas, bg="#0d0d0d")
        self.button_window = self.canvas.create_window(0, 0, window=self.button_frame, anchor="n")

        self.canvas.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        width, height = event.width, event.height
        if width < 10 or height < 10:
            return

        self.canvas.coords(self.bg_rect_id, 0, 0, width, height)

        if self._bg_pil is not None:
            self._bg_photo = self._make_cover_image(width, height)
            if self._bg_image_id is None:
                self._bg_image_id = self.canvas.create_image(0, 0, anchor="nw", image=self._bg_photo)
                self.canvas.tag_lower(self._bg_image_id)
            else:
                self.canvas.itemconfig(self._bg_image_id, image=self._bg_photo)
                self.canvas.coords(self._bg_image_id, 0, 0)

        title_y = height * 0.16
        self.canvas.coords(self.title_shadow_id, width / 2 + 3, title_y + 3)
        self.canvas.coords(self.title_id, width / 2, title_y)
        self.canvas.coords(self.subtitle_id, width / 2, title_y + 42)

        divider_y = title_y + 72
        half = min(120, width * 0.14)
        cx = width / 2
        self.canvas.coords(self.divider_left_id, cx - half, divider_y, cx - 14, divider_y)
        self.canvas.coords(self.divider_right_id, cx + 14, divider_y, cx + half, divider_y)
        d = 6
        self.canvas.coords(
            self.divider_diamond_id,
            cx, divider_y - d, cx + d, divider_y, cx, divider_y + d, cx - d, divider_y,
        )

        self.canvas.coords(self.button_window, width / 2, divider_y + 30)
        self.canvas.coords(self.status_text_id, width / 2, height * 0.9)

    def _make_cover_image(self, width, height):
        """Resize+crop self._bg_pil so it fills width x height with no distortion."""
        img = self._bg_pil
        img_ratio = img.width / img.height
        target_ratio = width / height
        if img_ratio > target_ratio:
            new_height = height
            new_width = int(height * img_ratio)
        else:
            new_width = width
            new_height = int(width / img_ratio)
        resized = img.resize((max(new_width, 1), max(new_height, 1)))
        left = (new_width - width) // 2
        top = (new_height - height) // 2
        cropped = resized.crop((left, top, left + width, top + height))
        return ImageTk.PhotoImage(cropped)

    def _clear_buttons(self):
        for widget in self.button_frame.winfo_children():
            widget.destroy()

    def _set_status(self, text):
        self.canvas.itemconfig(self.status_text_id, text=text)

    # ----- styled button helper -----

    def _add_button(self, parent, text, bg, fg, command, border=GOLD, width=26):
        """A tk.Button dressed up with a thin colored border and a hover
        highlight, instead of the default flat OS button look."""
        wrapper = tk.Frame(parent, bg=border)
        btn = tk.Button(
            wrapper, text=text, font=self.btn_font, width=width, bg=bg, fg=fg,
            relief="flat", bd=0, cursor="hand2", command=command,
            activebackground=_lighten(bg), activeforeground=fg,
        )
        btn.pack(padx=2, pady=2, ipady=6)
        hover = _lighten(bg)
        btn.bind("<Enter>", lambda e: btn.config(bg=hover))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg))
        wrapper.pack(pady=6)
        return wrapper

    # ----- login buttons (fresh sign-in) -----

    def _show_login_buttons(self):
        self._clear_buttons()
        self._add_button(self.button_frame, "Sign in with Google", "#ffffff", "#1a1a1a", self._on_google_click)
        self._add_button(self.button_frame, "Sign in / Sign up with Email", "#2a4d8f", "white", self._show_local_form)
        self._add_button(self.button_frame, "Continue as Guest (30 days)", "#8b1e1e", "white", self._on_guest_click)

    # ----- email / password form -----

    def _show_local_form(self):
        self._clear_buttons()
        self._set_status("")

        entry_kwargs = dict(font=self.btn_font, width=26, bg=CARD_BG, fg="white",
                             insertbackground="white", relief="flat")

        def labeled_entry(label_text, show=None):
            tk.Label(self.button_frame, text=label_text, font=self.sub_font,
                      bg="#0d0d0d", fg="#aaaaaa").pack(pady=(0, 2))
            var = tk.StringVar()
            border = tk.Frame(self.button_frame, bg=GOLD_DIM)
            entry = tk.Entry(border, textvariable=var, show=show, **entry_kwargs)
            entry.pack(padx=1, pady=1, ipady=3)
            border.pack(pady=(0, 6))
            return var

        self._local_name_var = labeled_entry("Name (for sign up)")
        self._local_email_var = labeled_entry("Email")
        self._local_password_var = labeled_entry("Password", show="•")

        row = tk.Frame(self.button_frame, bg="#0d0d0d")
        row.pack(pady=(4, 4))
        self._add_button(row, "Log In", "#1e5f2e", "white", self._on_local_login, width=12)
        self._add_button(row, "Sign Up", "#8b1e1e", "white", self._on_local_signup, width=12)
        for child in row.winfo_children():
            child.pack_configure(side="left", padx=3)

        self._add_button(self.button_frame, "Back", "#333333", "white", self._show_login_buttons)

    def _local_form_inputs(self):
        return (
            self._local_name_var.get().strip() or "Player",
            self._local_email_var.get().strip(),
            self._local_password_var.get(),
        )

    def _on_local_login(self):
        _, email, password = self._local_form_inputs()
        if not email or not password:
            self._set_status("Enter email and password")
            return
        try:
            database.check_connection()
        except Exception:
            self._set_status("Can't reach MongoDB — is it running locally?")
            return
        try:
            user_id = auth.local_sign_in(email, password)
            self._finish(user_id)
        except auth.AuthError as e:
            self._set_status(str(e))

    def _on_local_signup(self):
        name, email, password = self._local_form_inputs()
        if not email or not password:
            self._set_status("Enter email and password")
            return
        try:
            database.check_connection()
        except Exception:
            self._set_status("Can't reach MongoDB — is it running locally?")
            return
        try:
            user_id = auth.local_sign_up(email, name, password)
            self._finish(user_id)
        except auth.AuthError as e:
            self._set_status(str(e))

    # ----- welcome back (existing valid session found) -----

    def _show_welcome_back(self, user_id):
        user = database.get_user(user_id)
        if not user:
            self._show_login_buttons()
            return

        name = user.get("name") or "Guest"
        self._set_status(
            f"Welcome back, {name}"
            + (f" — guest access until {user['expires_at'].date()}" if user["auth_type"] == "guest" else "")
        )

        self._clear_buttons()
        self._add_button(self.button_frame, "Continue", "#1e5f2e", "white", lambda: self._finish(user_id))
        self._add_button(self.button_frame, "Back — Sign in as someone else", "#333333", "white", self._on_back_click)
        self._add_button(self.button_frame, "Delete this account", "#5a1010", "white",
                          lambda: self._on_delete_click(user_id))

    def _on_back_click(self):
        auth.clear_session()
        self._set_status("")
        self._show_login_buttons()

    def _on_delete_click(self, user_id):
        auth.delete_account(user_id)
        self._set_status("Account deleted")
        self._show_login_buttons()

    # ----- auto login on launch -----

    def _try_auto_login(self):
        try:
            database.check_connection()
        except Exception:
            self._set_status("Can't reach MongoDB — is it running locally?")
            return

        user_id = auth.load_saved_session()
        if user_id:
            self._show_welcome_back(user_id)

    # ----- guest -----

    def _on_guest_click(self):
        try:
            database.check_connection()
        except Exception:
            self._set_status("Can't reach MongoDB — is it running locally?")
            return
        user_id, expires_at = auth.create_guest()
        self._set_status(f"Playing as guest until {expires_at.date()}")
        self._finish(user_id)

    # ----- google (runs in a thread so the browser popup doesn't freeze the UI) -----

    def _on_google_click(self):
        self._set_status("Opening browser for Google sign-in…")
        threading.Thread(target=self._google_worker, daemon=True).start()
        self.after(200, self._poll_google_result)

    def _google_worker(self):
        try:
            user_id = auth.google_sign_in()
            self.result_queue.put(("ok", user_id))
        except Exception as e:
            self.result_queue.put(("error", str(e)))

    def _poll_google_result(self):
        try:
            status, payload = self.result_queue.get_nowait()
        except queue.Empty:
            self.after(200, self._poll_google_result)
            return

        if status == "ok":
            self._finish(payload)
        else:
            self._set_status(f"Google sign-in failed: {payload}")

    # ----- done -----

    def _finish(self, user_id):
        self.user_id = user_id
        self.destroy()