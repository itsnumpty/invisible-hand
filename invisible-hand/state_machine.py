import pytesseract
import time

from collections import deque

# Custom functions
from keypress import PressAndReleaseKey, MultiPressKey
from screenread import GameWindowHandler
from config import bot_name
from ocr_processor import OCRProcessor

# Set the OCR executable location
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class State:
    """Represents a state in the state machine.

    Attributes:
        name (str): The name of the state.
        transitions (dict): A dictionary mapping inputs to target states and actions.
    """
    def __init__(self, name):
        """Initializes the state with a name.

        Args:
            name (str): The name of the state.
        """
        self.name = name
        self.transitions = {}

    def add_transition(self, input, target_state, action):
        """Adds a transition to another state.

        Args:
            input (str): The input that triggers the transition.
            target_state (State): The target state to transition to.
            action (callable): The action to perform during the transition.
        """
        self.transitions[input] = (target_state, action)

    def get_transition(self, input):
        """Gets the transition associated with the given input.

        Args:
            input (str): The input to look up.

        Returns:
            tuple: A tuple containing the target state and action, or None if no transition exists.
        """
        return self.transitions.get(input, None)

class StateMachine:
    """Manages the current state and transitions between states.

    Attributes:
        current_state (State): The current state of the state machine.
    """
    def __init__(self, initial_state):
        """Initializes the state machine with an initial state.

        Args:
            initial_state (State): The initial state of the state machine.
        """
        self.current_state = initial_state

    def transition(self, input):
        """Transitions to a new state based on the input.

        Args:
            input (str): The input that triggers the transition.

        Returns:
            bool: True if the transition was successful, False otherwise.
        """
        transition = self.current_state.get_transition(input)
        if transition is None:
            print(f"No transition for input {input} from state {self.current_state.name}")
            return False
        target_state, action = transition
        print(f"Transitioning from {self.current_state.name} to {target_state.name} on input {input}")
        action()
        self.current_state = target_state
        return True

class OCRBasedStateMachine(StateMachine):
    """State machine that uses OCR to detect the current state and transition accordingly.

    Attributes:
        ocr_processor (OCRProcessor): The OCR processor used to read the screen.
        states_info (dict): A dictionary mapping state names to their respective ROIs and texts.
    """
    
    def __init__(self, states, ocr_processor, states_info, max_retries=2, retry_action=None):
        """Initializes the OCR-based state machine with OCR processor and states info.

        Args:
            states (dict): A dictionary mapping state names to State objects.
            ocr_processor (OCRProcessor): The OCR processor used to read the screen.
            states_info (dict): A dictionary mapping state names to their respective ROIs and texts.
            max_retries (int): Maximum number of retries to detect the initial state.
            retry_action (callable): Optional action to perform before each retry.
        """
        self.states = states
        self.ocr_processor = ocr_processor
        self.states_info = states_info
        self.max_retries = max_retries
        self.retry_action = retry_action or (lambda: PressAndReleaseKey('DIK_ESCAPE', 1))
        
        initial_state = self.detect_initial_state_with_retries()
        super().__init__(initial_state)
        
    def detect_initial_state_with_retries(self):
        """Detects the initial state with retries.

        Tries to detect the initial state, and retries if detection fails.

        Returns:
            State: The detected initial state.

        Raises:
            ValueError: If the initial state could not be detected after max_retries.
        """
        for attempt in range(self.max_retries):
            try:
                return self._detect_initial_state()
            except ValueError:
                if attempt < self.max_retries - 1:
                    self.retry_action()
                else:
                    raise ValueError("Failed to detect the initial state after maximum retries")

    def _detect_initial_state(self):
        """Detects the initial state using OCR and ROIs.

        Returns:
            State: The detected initial state.
        """
        handler = GameWindowHandler()
        image = handler.capture_window()
        detected_state_name = self.ocr_processor.find_text_in_rois(image, self.states_info)
        if detected_state_name:
            print(f"Detected initial state: {detected_state_name}")
            return self.states[detected_state_name]
        raise ValueError("Failed to detect initial state.")

    def detect_and_transition(self, target_state_name):
        """Detects the current state using OCR and transitions to the target state if needed.

        Args:
            target_state_name (str): The name of the target state to transition to.

        Returns:
            bool: True if the transition was successful, False otherwise.
        """
        if self.current_state.name == target_state_name:
            print(f"Already in the {target_state_name} state.")
            return True
        
        handler = GameWindowHandler()
        image = handler.capture_window()
        
        detected_state_name = self.ocr_processor.find_text_in_rois(image, self.states_info)
        if detected_state_name:
            print(f"Detected state: {detected_state_name}")
            self.current_state = self.states[detected_state_name]
        
        if self.current_state.name == target_state_name:
            print(f"Already in the {target_state_name} state.")
            return True

        path = self._find_path(target_state_name)
        if path is None:
            print(f"No path found to {target_state_name}")
            return False

        print(f"Path to {target_state_name}: {[state.name for state in path]}")

        # Ensure focus
        handler.pull_foreground()

        for state in path[1:]:
            # Find the input string that transitions to the next state
            for input, (target_state, action) in self.current_state.transitions.items():
                if target_state.name == state.name:
                    print(f"Transitioning from {self.current_state.name} to {target_state.name} on input {input}")
                    action()
                    self.current_state = target_state
                    
                    # Capture window and verify state after action
                    handler = GameWindowHandler()
                    image = handler.capture_window()
                    detected_state_name = self.ocr_processor.find_text_in_rois(image, self.states_info)
                    if detected_state_name == target_state_name:
                        print(f"Reached target state: {target_state_name}")
                        return True
                    break
            else:
                print(f"No valid transition found from {self.current_state.name} to {state.name}")
                return False
        print(f"Failed to transition to {target_state_name} state.")
        self.ocr_processor.debug_save_image(target_state_name)
        return False
    
    def _find_path(self, target_state_name):
        """Finds the path from the current state to the target state.

        Args:
            target_state_name (str): The name of the target state.

        Returns:
            list: A list of states representing the path to the target state, or None if no path is found.
        """
        queue = deque([(self.current_state, [])])
        visited = set()

        while queue:
            current_state, path = queue.popleft()
            if current_state.name == target_state_name:
                return path + [current_state]

            visited.add(current_state)
            for input, (next_state, action) in current_state.transitions.items():
                if next_state not in visited:
                    queue.append((next_state, path + [current_state]))

        return None

    def _follow_path(self, path):
        """Follows the given path to transition to the target state.

        Args:
            path (list): A list of states representing the path to follow.
        """
        for state in path:
            self.detect_and_transition(state.name)

def _create_press_and_release_action(key, duration=0.2):
    """Creates an action that presses and releases a key.

    Args:
        key (str): The key to press and release.
        duration (float): The duration to hold the key.

    Returns:
        callable: An action that presses and releases the key.
    """
    return lambda: PressAndReleaseKey(key, duration)

def _create_multi_press_action(key, presses=1, delay=0.3):
    """Creates an action that presses a key multiple times.

    Args:
        key (str): The key to press.
        presses (int): The number of presses.
        delay (float): The delay between presses.

    Returns:
        callable: An action that presses the key multiple times.
    """
    return lambda: MultiPressKey(key, presses, delay)

def create_states():
    """Creates and returns the states for the state machine.

    Returns:
        dict: A dictionary mapping state names to State objects.
    """
    return {
        "Main Menu": State("Main Menu"),
        "Play": State("Play"),
        "Scoreboard": State("Scoreboard"),
        "In Game": State("In Game"),
        "Menu": State("Menu"),
        "Multiplayer": State("Multiplayer"),
        "Advanced Search": State("Advanced Search"),
        "Created": State("Created"),
        "Game Info": State("Game Info"),
        "Deploy": State("Deploy"),
        "Round Starting": State("Round Starting")
    }


def create_transitions(state_ocr_processor):
    """Creates and returns the transitions for the state machine.

    Args:
        state_ocr_processor (OCRProcessor): The OCR processor used to detect text on the screen.

    Returns:
        dict: A dictionary mapping state names to their transitions.
    """
    return {
        'Main Menu': {
            'enter_play': ('Play', lambda: state_ocr_processor.find_and_click('PLAY', (0.052, 0.55, 0.1041, 0.8537)))
        },
        'Play': {
            'enter_multiplayer': ('Multiplayer', lambda: (state_ocr_processor.find_and_click('MULTIPLAYER', (0.39114, 0.175, 0.692, 0.873)), time.sleep(2)))
        },
        'Scoreboard': {
            'exit_to_main_menu': ('Main Menu', _create_press_and_release_action('DIK_ESCAPE', 1)),
            'exit_to_menu': ('Menu', _create_press_and_release_action('DIK_ESCAPE', 1))
        },
        'In Game': {
            'enter_main_menu': ('Main Menu', _create_press_and_release_action('DIK_ESCAPE', 1)),
            'enter_menu': ('Menu', lambda: _create_press_and_release_action('DIK_ESCAPE', 1)())
        },
        'Menu': {
            'enter_scoreboard': ('Scoreboard', lambda: (state_ocr_processor.find_and_click('SCOREBOARD', (0, 0, 0.15625, 0.786)), time.sleep(2))),
            'enter_game': ('In Game', lambda: _create_press_and_release_action('DIK_ESCAPE', 1)())
        },
        'Multiplayer': {
            'advanced_search': ('Advanced Search', lambda: (state_ocr_processor.find_and_click('ADVANCED', (0.7625, 0.1796, 0.97, 0.622)), time.sleep(2)))
        },
        'Advanced Search': {
            'enter_created': ('Created', lambda: state_ocr_processor.find_and_click('CREATED', (0, 0, 0.3, 0.25)))
        },
        'Created': {
            'game_info': ('Game Info', lambda: (state_ocr_processor.find_and_click('Borderless', (0.0364, 0.062, 0.365, 0.266)), time.sleep(2)))
        },
        'Game Info': {
            'enter_game': ('In Game', lambda: (state_ocr_processor.find_and_click('JOIN', (0, 0, 0.25, 0.5)), time.sleep(30)))
        },
        'Deploy': {
            'enter_game': ('In Game', lambda: (state_ocr_processor.find_and_click('DEPLOY', (0.8, 0.8, 2, 2)), time.sleep(6)))
        },
        'Round Starting': {
            'enter_deploy': ('Deploy', lambda: time.sleep(60))
        }
    }


def setup_transitions(states, transitions):
    """Sets up transitions for the given states.

    Args:
        states (dict): A dictionary mapping state names to State objects.
        transitions (dict): A dictionary mapping state names to their transitions.
    """
    for state_name, state_transitions in transitions.items():
        state = states[state_name]
        for input, (target_state_name, action) in state_transitions.items():
            target_state = states[target_state_name]
            state.add_transition(input, target_state, action)


def create_states_info():
    """Creates and returns the states info for OCR detection.

    Returns:
        dict: A dictionary mapping state names to their respective ROIs and texts.
    """
    return {
        'Main Menu': {'roi': (0.052, 0.55, 0.1041, 0.8537), 'text': 'PLAY'},
        'Play': {'roi': (0, 0, 0.2, 0.2), 'text': 'PLAY'},
        'Menu': {'roi': (0, 0, 0.3, 0.25), 'text': 'MENU'},
        'Scoreboard': {'roi': (0, 0, 0.3, 0.25), 'text': 'SCOREBOARD'},
        'Multiplayer': {'roi': (0, 0, 0.2, 0.2), 'text': 'MULTIPLAYER'},
        'Advanced Search': {'roi': (0, 0, 0.3, 0.25), 'text': 'ADVANCED'},
        'Created': {'roi': (0, 0, 0.3, 0.25), 'text': 'CREATED'},
        'In Game': {'roi': (0, 0.7, 0.271, 1), 'text': bot_name},
        'Game Info': {'roi': (0, 0, 0.3, 0.25), 'text': 'GAME'},
        'Deploy': {'roi': (0.8, 0.8, 2, 2), 'text': 'DEPLOY'},
        'Round Starting': {'roi': (0.8, 0.8, 2, 2), 'text': 'ROUND'}
    }


def create_state_handler():
    """Creates and returns an OCR-based state machine handler.

    Returns:
        OCRBasedStateMachine: The initialized OCR-based state machine.
    """
    states = create_states()
    handler = GameWindowHandler()
    state_ocr_processor = OCRProcessor(handler)
    transitions = create_transitions(state_ocr_processor)
    setup_transitions(states, transitions)
    states_info = create_states_info()
    return OCRBasedStateMachine(states, state_ocr_processor, states_info)