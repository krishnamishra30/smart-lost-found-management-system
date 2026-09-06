import os
import mysql.connector
from mysql.connector import Error


# ==========================================
# DATABASE CONFIGURATION
# ==========================================

DB_HOST = os.environ.get(
    "DB_HOST",
    "localhost"
).strip()

try:
    DB_PORT = int(
        os.environ.get(
            "DB_PORT",
            "3306"
        )
    )
except ValueError:
    DB_PORT = 3306

DB_USER = os.environ.get(
    "DB_USER",
    "root"
).strip()

DB_PASSWORD = os.environ.get(
    "DB_PASSWORD",
    ""
)

DB_NAME = os.environ.get(
    "DB_NAME",
    "smart_lost_found"
).strip()

DB_SSL_CA = os.environ.get(
    "DB_SSL_CA",
    ""
).strip()


# ==========================================
# DATABASE CONNECTION
# ==========================================

def get_db_connection():

    try:

        # --------------------------------------
        # Local MySQL
        # --------------------------------------

        if DB_HOST in {
            "localhost",
            "127.0.0.1"
        }:

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

        # --------------------------------------
        # Remote MySQL - Aiven / Render
        # --------------------------------------

        else:

            connection_config = {
                "host": DB_HOST,
                "port": DB_PORT,
                "user": DB_USER,
                "password": DB_PASSWORD,
                "database": DB_NAME,
                "connection_timeout": 20,
                "autocommit": False,
                "use_pure": True,

                "ssl_verify_cert": False,
                "ssl_verify_identity": False
            }

            if DB_SSL_CA:
                connection_config["ssl_ca"] = DB_SSL_CA

            connection = mysql.connector.connect(
                **connection_config
            )

        # --------------------------------------
        # Check Connection
        # --------------------------------------

        if connection.is_connected():

            print(
                "MYSQL CONNECTION SUCCESSFUL"
            )

            print(
                "Connected Database:",
                DB_NAME
            )

            return connection

        connection.close()

    except Error as error:

        print(
            "DATABASE CONNECTION ERROR:",
            str(error)
        )

    except Exception as error:

        print(
            "DATABASE CONNECTION ERROR:",
            str(error)
        )

    return None