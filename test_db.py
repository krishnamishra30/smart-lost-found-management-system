import mysql.connector
from database import get_db_connection


def test_mysql_connection():

    db = None
    cursor = None

    try:
        # Connect to MySQL
        db = get_db_connection()

        if db is None:
            print("================================")
            print("MYSQL CONNECTION FAILED")
            print("ERROR: Could not establish database connection.")
            print("================================")
            return

        print("================================")
        print("MYSQL CONNECTION SUCCESSFUL")
        print("================================")

        # Create cursor
        cursor = db.cursor()

        # Check connected database
        cursor.execute("SELECT DATABASE()")

        result = cursor.fetchone()

        if result:
            print("Connected Database:", result[0])
        else:
            print("Connected Database: Unknown")

        print("================================")

    except Exception as e:

        print("================================")
        print("MYSQL CONNECTION FAILED")
        print("ERROR:", e)
        print("================================")

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


if __name__ == "__main__":
    test_mysql_connection()