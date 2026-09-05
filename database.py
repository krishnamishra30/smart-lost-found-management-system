import mysql.connector
from mysql.connector import Error


def get_db_connection():
    """
    Create and return a MySQL database connection.
    """

    try:
        connection = mysql.connector.connect(
            host="localhost",
            port=3306,
            user="root",
            password="3012",
            database="smart_lost_found",
            connection_timeout=10
        )

        if connection.is_connected():
            return connection

    except Error as e:
        print("DATABASE CONNECTION ERROR:", e)

    return None