"""
Start screen: mafia-themed title screen with Sign in with Google / Play
as Guest. Layout is fully responsive — it redraws on every resize, so
fullscreen and windowed both look correct.

Swap BG_IMAGE_PATH to a real background once you have art. If Pillow
is installed, the image is scaled to cover the window at any size;
without Pillow it's shown at its native size, anchored top-left.
"""

import os
import queue
import threading
import tkinter as tk
from tkinter import font as tkfont

import auth
import database

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

BG_IMAGE_PATH = "assets/mafia_background.png"  # drop your background here later


class LoginScreen(tk.Tk):
    def __init__(self, start_fullscreen=False):
        super().__init__()
        self.title("Mafia Blackjack")
        self.geometry("900x600")
        self.configure(bg="#0d0d0d")

        self.result_queue = queue.Queue()
        self.user_id = None  # set on success, read by main.py after mainloop exits
        self._is_fullscreen = False
        self._bg_pil = None
        self._bg_photo = None
        self._bg_image_id = None
        self._last_size = (0, 0)

        if PIL_AVAILABLE and os.path.exists(BG_IMAGE_PATH):
            self._bg_pil = Image.open(BG_IMAGE_PATH)

        self.title_font = tkfont.Font(family="Georgia", size=36, weight="bold")
        self.sub_font = tkfont.Font(family="Georgia", size=13, slant="italic")
        self.btn_font = tkfont.Font(family="Helvetica", size=13, weight="bold")

        self._build_window_controls()
        self._build_canvas()
        self._show_login_buttons()
        self._try_auto_login()

        if start_fullscreen:
            self._is_fullscreen = True
            self.attributes("-fullscreen", True)

        self._bring_to_front()

    def _bring_to_front(self):
        """Guards against the window opening minimized/unfocused on some OSes."""
        self.deiconify()
        self.state("normal")
        self.lift()
        self.attributes("-topmost", True)
        self.after(50, lambda: self.attributes("-topmost", False))
        self.focus_force()

    # ----- fullscreen / minimize -----

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

        self.bind("<F11>", lambda e: self._toggle_fullscreen())
        self.bind("<Escape>", lambda e: self._exit_fullscreen())

    def _toggle_fullscreen(self):
        self._is_fullscreen = not self._is_fullscreen
        self.attributes("-fullscreen", self._is_fullscreen)

    def _exit_fullscreen(self):
        self._is_fullscreen = False
        self.attributes("-fullscreen", False)

    # ----- responsive canvas -----

    def _build_canvas(self):
        self.canvas = tk.Canvas(self, bg="#0d0d0d", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.bg_rect_id = self.canvas.create_rectangle(0, 0, 1, 1, fill="#111318", outline="")
        self.accent_rect_id = self.canvas.create_rectangle(0, 0, 1, 1, fill="#0b5d2e", outline="")
        self.title_id = self.canvas.create_text(0, 0, text="MAFIA BLACKJACK", font=self.title_font, fill="#d4af37")
        self.subtitle_id = self.canvas.create_text(0, 0, text="the house always has a cut", font=self.sub_font, fill="#cfcfcf")
        self.status_text_id = self.canvas.create_text(0, 0, text="", font=self.btn_font, fill="#e0e0e0")

        # buttons live in a plain frame so we can swap its contents between
        # "login" mode and "welcome back" mode without rebuilding everything
        self.button_frame = tk.Frame(self.canvas, bg="#111318")
        self.button_window = self.canvas.create_window(0, 0, window=self.button_frame, anchor="n")

        self.canvas.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        width, height = event.width, event.height
        if width < 10 or height < 10:
            return
        self._last_size = (width, height)

        self.canvas.coords(self.bg_rect_id, 0, 0, width, height)
        self.canvas.coords(self.accent_rect_id, 0, height * 0.7, width, height)

        if self._bg_pil is not None:
            self._bg_photo = self._make_cover_image(width, height)
            if self._bg_image_id is None:
                self._bg_image_id = self.canvas.create_image(0, 0, anchor="nw", image=self._bg_photo)
                self.canvas.tag_lower(self._bg_image_id)  # keep it behind everything else
            else:
                self.canvas.itemconfig(self._bg_image_id, image=self._bg_photo)
                self.canvas.coords(self._bg_image_id, 0, 0)

        self.canvas.coords(self.title_id, width / 2, height * 0.18)
        self.canvas.coords(self.subtitle_id, width / 2, height * 0.18 + 45)
        self.canvas.coords(self.button_window, width / 2, height * 0.32)
        self.canvas.coords(self.status_text_id, width / 2, height * 0.85)

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

    # ----- login buttons (fresh sign-in) -----

    def _show_login_buttons(self):
        self._clear_buttons()
        tk.Button(
            self.button_frame, text="Sign in with Google", font=self.btn_font, width=26,
            bg="#ffffff", fg="#1a1a1a", relief="flat", command=self._on_google_click
        ).pack(pady=6)
        tk.Button(
            self.button_frame, text="Sign in / Sign up with Email", font=self.btn_font, width=26,
            bg="#2a4d8f", fg="white", relief="flat", command=self._show_local_form
        ).pack(pady=6)
        tk.Button(
            self.button_frame, text="Continue as Guest (30 days)", font=self.btn_font, width=26,
            bg="#8b1e1e", fg="white", relief="flat", command=self._on_guest_click
        ).pack(pady=6)

    # ----- email / password form -----

    def _show_local_form(self):
        self._clear_buttons()
        self._set_status("")

        entry_kwargs = dict(font=self.btn_font, width=26, bg="#1c1c1c", fg="white",
                             insertbackground="white", relief="flat")

        tk.Label(self.button_frame, text="Name (for sign up)", font=self.sub_font,
                  bg="#111318", fg="#aaaaaa").pack(pady=(0, 2))
        self._local_name_var = tk.StringVar()
        tk.Entry(self.button_frame, textvariable=self._local_name_var, **entry_kwargs).pack(pady=(0, 6))

        tk.Label(self.button_frame, text="Email", font=self.sub_font,
                  bg="#111318", fg="#aaaaaa").pack(pady=(0, 2))
        self._local_email_var = tk.StringVar()
        tk.Entry(self.button_frame, textvariable=self._local_email_var, **entry_kwargs).pack(pady=(0, 6))

        tk.Label(self.button_frame, text="Password", font=self.sub_font,
                  bg="#111318", fg="#aaaaaa").pack(pady=(0, 2))
        self._local_password_var = tk.StringVar()
        tk.Entry(self.button_frame, textvariable=self._local_password_var, show="•", **entry_kwargs).pack(pady=(0, 8))

        row = tk.Frame(self.button_frame, bg="#111318")
        row.pack(pady=(0, 4))
        tk.Button(
            row, text="Log In", font=self.btn_font, width=12,
            bg="#1e5f2e", fg="white", relief="flat", command=self._on_local_login
        ).pack(side="left", padx=3)
        tk.Button(
            row, text="Sign Up", font=self.btn_font, width=12,
            bg="#8b1e1e", fg="white", relief="flat", command=self._on_local_signup
        ).pack(side="left", padx=3)

        tk.Button(
            self.button_frame, text="Back", font=self.btn_font, width=26,
            bg="#333333", fg="white", relief="flat", command=self._show_login_buttons
        ).pack(pady=(4, 0))

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
        tk.Button(
            self.button_frame, text="Continue", font=self.btn_font, width=26,
            bg="#1e5f2e", fg="white", relief="flat",
            command=lambda: self._finish(user_id)
        ).pack(pady=6)
        tk.Button(
            self.button_frame, text="Back — Sign in as someone else", font=self.btn_font, width=26,
            bg="#333333", fg="white", relief="flat", command=self._on_back_click
        ).pack(pady=6)
        tk.Button(
            self.button_frame, text="Delete this account", font=self.btn_font, width=26,
            bg="#5a1010", fg="white", relief="flat",
            command=lambda: self._on_delete_click(user_id)
        ).pack(pady=6)

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