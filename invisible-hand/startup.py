import win32gui
import subprocess
import config
import time

class Startup:
    """Handles the startup process of the game, including locating and launching the game window."""

    def __init__(self) -> None:
        """Initializes the Startup class with the game window title and starts the game."""
        self.window_title = config.game_window_name
        self.start_game()

    def get_game_window_handle(self):
        """Finds and returns the handle for the game window.

        Returns:
            int: The handle of the game window if found, otherwise None.
        """
        window_handle = win32gui.FindWindow(None, self.window_title)
        if window_handle == 0:
            return None
        return window_handle
    
    def start_game(self):
        """Starts the game if the game window handle is not found.

        Attempts to launch the game executable specified in the configuration.
        Waits for 120 seconds to allow the game to start.
        """
        game_path = config.game_location
        self.hwnd = self.get_game_window_handle()
        if not self.hwnd:
            try:
                subprocess.Popen([game_path])
                time.sleep(120)
            except Exception as e:
                print(f"Failed to start the game: {e}")
