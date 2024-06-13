import requests

from config import server_name

class ServerInfoRequester:
    """Handles requests to the server info API and processes server data."""

    def __init__(self, db):
        """Initializes the ServerInfoRequester with the database connection and server parameters.

        Args:
            db: The database connection object.
        """
        self.url = 'https://api.gametools.network/bfv/players/'
        self.params = {'name': server_name}
        self.headers = {'accept': 'application/json'}
        self.server_map = self.get_server_map()
        self.db = db

    def get_server_info(self) -> dict:
        """Fetches server information from the API.

        Returns:
            dict: The server information data if the request is successful, otherwise an empty dictionary.
        """
        try:
            response = requests.get(self.url, params=self.params, headers=self.headers)
            return response.json()
        except requests.RequestException as e:
            return {}
        
    def get_players(self):
        """Retrieves the list of players currently on the server.

        Returns:
            list: A list of player names if the request is successful, otherwise None.
        """
        try:
            server_info = self.get_server_info()
            players = []
            for team in server_info['teams']:
                for player in team['players']:
                    players.append(player['name'])
            return players
        except Exception as e:
            print(f'Error: {e}')
            return None
        
    def is_server_up(self):
        """Checks if the server is up and running.

        Returns:
            bool: True if the server is up, False otherwise.
        """
        server_info = self.get_server_info()
        if server_info is None:
            return False
        errors = server_info.get('errors')
        if errors and errors[0] == 'server not found':
            return False
        return True
    
    def get_server_map(self):
        """Fetches the current map of the server.

        Returns:
            str: The name of the current map.
        """
        server_info = self.get_server_info()
        return server_info['serverinfo']['level']
    
    def server_game_change(self):
        """Checks if the server's game map has changed.

        Returns:
            bool: True if the map has changed, False otherwise.
        """
        current_map = self.get_server_map()
        if not current_map == self.server_map:
            self.server_map = current_map
            return True
        return False