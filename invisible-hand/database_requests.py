import mysql.connector
from mysql.connector import errorcode
from config import DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT

class DatabaseRequests:
    """Handles database connections and queries for a MySQL database."""

    def __init__(self) -> None:
        """Initializes the DatabaseRequests class with connection and cursor set to None."""
        self.conn = None
        self.cur = None

    def __enter__(self):
        """Establishes the database connection when entering a context.

        Returns:
            DatabaseRequests: The instance of the DatabaseRequests class.
        """
        self.get_conn()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Closes the database connection when exiting a context.

        Args:
            exc_type (type): The exception type.
            exc_val (Exception): The exception instance.
            exc_tb (traceback): The traceback object.
        """
        self.close_conn()

    def get_conn(self):
        """Establishes the database connection if not already connected."""
        if self.conn is None or not self.conn.is_connected():
            try:
                self.conn = mysql.connector.connect(
                    user=DB_USER,
                    password=DB_PASSWORD,
                    host=DB_HOST,
                    database=DB_NAME,
                    port=DB_PORT
                )
                self.cur = self.conn.cursor()
            except mysql.connector.Error as err:
                if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                    print("Something is wrong with your user name or password")
                elif err.errno == errorcode.ER_BAD_DB_ERROR:
                    print("Database does not exist")
                else:
                    print(err)

    def execute_query(self, query, params=None):
        """Executes a given SQL query with optional parameters.

        Args:
            query (str): The SQL query to execute.
            params (tuple, optional): The parameters to use with the query. Defaults to None.
        """
        self.get_conn()  # Ensure the connection is established
        try:
            if params:
                self.cur.execute(query, params)
            else:
                self.cur.execute(query)
            self.conn.commit()
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            self.conn.rollback()

    def execute_read_query(self, query, params):
        """Executes a read (SELECT) query and returns the results.

        Args:
            query (str): The SQL query to execute.
            params (tuple): The parameters to use with the query.

        Returns:
            list: The result of the query as a list of dictionaries.
        """
        self.get_conn()  # Ensure the connection is established
        result = None

        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute(query, params)
            result = cursor.fetchall()
        except Exception as e:
            print(f'Error: {e}')
        finally:
            if cursor:
                cursor.close()
        return result

    def close_conn(self):
        """Closes the database connection and cursor."""
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()
        self.cur = None
        self.conn = None
