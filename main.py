from login_gui import LoginScreen
from gui import BlackjackGUI

if __name__ == "__main__":
    fullscreen = False

    while True:
        login = LoginScreen(start_fullscreen=fullscreen)
        login.mainloop()
        fullscreen = login._is_fullscreen

        if not login.user_id:
            print("No session — closing.")
            break

        app = BlackjackGUI(login.user_id, start_fullscreen=fullscreen)
        app.mainloop()
        fullscreen = app._is_fullscreen

        if not app.go_to_menu:
            break