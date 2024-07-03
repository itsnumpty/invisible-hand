import time
import schedule
import pyautogui

from database_requests import DatabaseRequests
from screenread import GameWindowHandler, GameWindowNotFoundException
from keypress import PressAndReleaseKey, MultiPressKey
from startup import Startup
from server_info import ServerInfoRequester
from ocr_processor import OCRProcessor
from state_machine import create_state_handler

class InvisibleHand:
    """Main class that handles everything to do with the game interactions."""
    def __init__(self):
        # Initialize the classses that control the game
        self.db = DatabaseRequests()
        self.server = ServerInfoRequester(self.db)
        self.startup = Startup()
        self.state_handler = create_state_handler()

        self.running = True
        self.scale_factor = 2

        self.state_handler.detect_and_transition("Scoreboard")

        self.schedule_jobs()

    def run(self):
        """Main entrypoint of the script. This will establish a window handler for the game."""
        while self.running:
            try:
                # Create a GameWindowHandler instance to check the game window
                self.handler = GameWindowHandler()

                # Run any pending jobs
                schedule.run_pending()
                   
            except GameWindowNotFoundException:
                # If the game window is not found, relaunch the game
                print("Game window not found. Relaunching the game...")
                self.relaunch_game()

    def kick_pingers(self):
        ocr = OCRProcessor(self.handler, self.scale_factor)
        kick_players = ocr.find_players_to_kick()
        if not kick_players: # If it's empty just skip
            return
        
        for player in kick_players:
            print(f"Player {player['name']} in {player['team']} is being kicked for ping of {player['latency']}")
            try:
                coords = ocr.find_player_coords(player['name'], player['team'])
                if coords: # Ensure player was found
                    x, y = coords
                    if self.is_within_screen(x, y):
                        self.handler.pull_foreground()
                        pyautogui.moveTo(x, y)
                        pyautogui.click()
                        pyautogui.moveTo(526, 1009) # Kick button location
                        pyautogui.click()
                        time.sleep(0.5)
                        if self.validate_kick(player['name']):
                            pyautogui.moveTo(898, 655) # Confirm kick
                            pyautogui.click()
                    else:
                        print(f"Coordinates ({x}, {y}) are outside the screen bounds.")
            except pyautogui.FailSafeException:
                print("PyAutoGUI fail-safe triggered. Script aborted to prevent out-of-control behavior.")
                break
            except Exception as e:
                print(f"An error occurred while processing player {player['name']}: {e}")
                break
    
    def validate_kick(self, player_name):
        image = self.handler.capture_window()
        ocr = OCRProcessor(self.handler, self.scale_factor)
        roi = (0.39, 0.42, 0.59, 0.499)
        ocr_data = ocr.perform_ocr_for_state_engine_text(image, roi)
        for text in ocr_data['text']:
            if player_name in text.strip():
                return True
            return False

    def relaunch_game(self):
        self.startup.start_game()
        for _ in range(5):
            print('Waiting 2 minutes for game to boot.')
            time.sleep(120)
            try:
                handler = GameWindowHandler()
                if handler.hwnd:
                    break
            except:
                continue
        print("Game has launched, checking server status...")
        if not self.server.is_server_up():
            print("Server is not up, launching...")
            self.launch_community_game()
        else:
            print("Server already up, joining session.")
            self.state_handler.detect_and_transition("Scoreboard")

    def check_game_change(self):
        print('Checking if map has changed')
        if self.server.server_game_change():
            print(f'Server has changed maps to {self.server.server_map}. Timing out.')
            time.sleep(60)
            self.state_handler.detect_and_transition("In Game")
            print('Timing out to allow scoreboard to settle.')
            time.sleep(120)
            self.state_handler.detect_and_transition("Scoreboard")
        else:
            print('Map not changed')

    def schedule_jobs(self):
        print('Scheduling jobs')
        schedule.every(20).seconds.do(self.check_game_change)
        schedule.every(2).seconds.do(self.kick_pingers)
        schedule.every(3).minutes.do(self.keep_player_alive)

    def launch_community_game(self):
        self.handler.pull_foreground()
        MultiPressKey('DIK_RIGHT', 2)
        PressAndReleaseKey('DIK_SPACE')
        for _ in range(5):
            time.sleep(2)
            ocr = OCRProcessor(self.handler, self.scale_factor)
            data, roi_coords = ocr.perform_ocr_for_text(roi=('Top', 0.3, 1, 1))
            coords = ocr.find_in_ocr(data, 'COMMUNITY', roi=roi_coords)
            if coords:
                break
        PressAndReleaseKey('DIK_RIGHT')
        time.sleep(0.2)
        PressAndReleaseKey('DIK_SPACE')

    def keep_player_alive(self):
        self.handler.pull_foreground()
        print('Keeping player alive')
        self.state_handler.detect_and_transition("In Game")
        time.sleep(2)
        PressAndReleaseKey('DIK_SPACE', 1)
        PressAndReleaseKey('DIK_W', 1)
        self.state_handler.detect_and_transition("Scoreboard")

    def is_within_screen(self, x, y):
        """Checks if the given coordinates are within the screen bounds.

        Args:
            x (int): The x-coordinate.
            y (int): The y-coordinate.

        Returns:
            bool: True if the coordinates are within the screen bounds, otherwise False.
        """
        screen_width, screen_height = pyautogui.size()
        return 0 <= x <= screen_width and 0 <= y <= screen_height