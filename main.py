"""
Mafia Blackjack entry point.

Flow: login -> home hub -> (shop | table) -> back to home hub -> ... -> logout
Each screen is its own Tk window; only one is ever open at a time.
Fullscreen state carries across every transition.
"""

from login_gui import LoginScreen
from home_gui import HomeScreen
from shop_gui import ShopScreen
from gui import BlackjackGUI

if __name__ == "__main__":
    fullscreen = False
    state = "login"
    user_id = None

    while state != "exit":
        if state == "login":
            login = LoginScreen(start_fullscreen=fullscreen)
            login.mainloop()
            fullscreen = login._is_fullscreen
            if login.user_id:
                user_id = login.user_id
                state = "home"
            else:
                state = "exit"

        elif state == "home":
            home = HomeScreen(user_id, start_fullscreen=fullscreen)
            home.mainloop()
            fullscreen = home._is_fullscreen
            if home.next_action == "shop":
                state = "shop"
            elif home.next_action == "play":
                state = "game"
            else:  # "logout" or window closed
                state = "login"

        elif state == "shop":
            shop = ShopScreen(user_id, start_fullscreen=fullscreen)
            shop.mainloop()
            fullscreen = shop._is_fullscreen
            state = "home"

        elif state == "game":
            game = BlackjackGUI(user_id, start_fullscreen=fullscreen)
            game.mainloop()
            fullscreen = game._is_fullscreen
            state = "home"

    print("Thanks for playing.")