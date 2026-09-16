"""
Shared window behavior so every screen (login, home, shop, game) behaves
the same way: fullscreen toggle, minimize, and not opening
minimized/unfocused. Subclass this instead of tk.Tk directly.
"""

import tkinter as tk


class BaseGameWindow(tk.Tk):
    def __init__(self, title, start_fullscreen=False):
        super().__init__()
        self.title(title)
        self.configure(bg="#0d0d0d")
        self._is_fullscreen = False
        self._fullscreen_requested = start_fullscreen

    def _bind_fullscreen_keys(self):
        self.bind("<F11>", lambda e: self._toggle_fullscreen())
        self.bind("<Escape>", lambda e: self._exit_fullscreen())

    def _toggle_fullscreen(self):
        self._is_fullscreen = not self._is_fullscreen
        self.attributes("-fullscreen", self._is_fullscreen)

    def _exit_fullscreen(self):
        self._is_fullscreen = False
        self.attributes("-fullscreen", False)

    def _bring_to_front(self):
        self.deiconify()
        self.state("normal")
        self.lift()
        self.attributes("-topmost", True)
        self.after(50, lambda: self.attributes("-topmost", False))
        self.focus_force()

    def _finish_setup(self):
        """Call once, after your layout is built, instead of manually
        handling fullscreen + focus."""
        if self._fullscreen_requested:
            self._is_fullscreen = True
            self.attributes("-fullscreen", True)
        self._bring_to_front()
