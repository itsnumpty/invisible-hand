import win32gui
import pyautogui
import numpy as np
import cv2
import time

import config

class GameWindowNotFoundException(Exception):
    """Exception raised when the game window is not found."""
    pass

class GameUnfocusedExeption(Exception):
    """Game window became unfocused. Terminating script."""
    pass

class GameWindowHandler:
    """Handles operations related to the game window, including capturing screenshots and setting window properties."""

    def __init__(self):
        """Initializes the GameWindowHandler with the game window title from the configuration."""
        self.window_title = config.game_window_name
        self.hwnd = self.get_game_window_handle()
        self.focused = False

        # Initialize
        self.window_x = None
        self.window_y = None
        self.w = None
        self.h = None

    def get_game_window_handle(self):
        """Finds and returns the game window handle.

        Raises:
            GameWindowNotFoundException: If the game window is not found.

        Returns:
            int: The handle of the game window.
        """
        window_handle = win32gui.FindWindow(None, self.window_title)
        if window_handle == 0:
            raise GameWindowNotFoundException("Game window not found")
        return window_handle
        
    def set_window_position_and_size(self, x, y, width, height):
        """Sets the position and size of the game window.

        Args:
            x (int): The x-coordinate of the window's new position.
            y (int): The y-coordinate of the window's new position.
            width (int): The new width of the window.
            height (int): The new height of the window.
        """
        if self.hwnd:
            win32gui.MoveWindow(self.hwnd, x, y, width, height, True)
            self.window_x = x
            self.window_y = y
            self.w = width
            self.h = height
        else:
            print("No game window handle found, cannot set position and size.")
    
    def pull_foreground(self):
        """Brings the game window to the foreground."""
        if self.hwnd:
            if not self.is_window_active():
                print('Setting foreground')
                try:
                    if not self.focused:
                        win32gui.SetForegroundWindow(self.hwnd)
                        self.focused = True
                        time.sleep(2)
                    else:
                        raise GameUnfocusedExeption
                except Exception as e:
                    print(f"Failed to set foreground window: {e}")
        else:
            print("No game window handle found, cannot set foreground.")
            # Attempt to re-fetch the window handle
            self.hwnd = self.get_game_window_handle()
        
    def is_window_active(self):
        """Checks if the game window is currently the active window.

        Returns:
            bool: True if the game window is active, False otherwise.
        """
        if self.hwnd:
            current_hwnd = win32gui.GetForegroundWindow()
            return current_hwnd == self.hwnd
        else:
            print("No game window handle found.")
            return False

    def capture_window(self):
        """Captures a screenshot of the game window.

        Returns:
            np.ndarray: The captured image of the game window if successful, otherwise None.
        """
        self.pull_foreground()

        if self.hwnd is None:
            print("No game window handle found, cannot capture window.")
            return None
        try:
            # Get the drawable area of the window
            rect = win32gui.GetWindowRect(self.hwnd)
            self.window_x, self.window_y, self.w, self.h = rect

            # Capture screenshot with pyautogui
            screenshot = pyautogui.screenshot(region=(self.window_x, self.window_y, self.w - self.window_x, self.h - self.window_y))

            # Convert the screenshot to a format cv2 can handle
            img = np.array(screenshot)
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

            current_timestamp = int(time.time())

            cv2.imwrite(f'debug/{current_timestamp}.png', img)

            return img

        except Exception as e:
            print(f"Failed to capture window: {e}")
            return None