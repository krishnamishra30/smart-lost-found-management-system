import mysql.connector
from mysql.connector import Error


# ==============================
# DATABASE CONFIGURATION
# ==============================

DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = "3012"
DB_NAME = "smart_lost_found"


# ==============================
# DATABASE CONNECTION
# ==============================

def get_db_connection():

    try:

        connection = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            connection_timeout=20,
            autocommit=False,
            use_pure=True
        )

        if connection.is_connected():

            print("MYSQL CONNECTION SUCCESSFUL")

            return connection

        connection.close()

    except Error as e:

        print(
            "DATABASE CONNECTION ERROR:",
            str(e)
        )

    except Exception as e:

        print(
            "DATABASE CONNECTION ERROR:",
            str(e)
        )

    return None