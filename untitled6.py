import mysql.connector
from mysql.connector import Error


def test_database():

    db = None
    cursor = None

    try:

        # --------------------------------------
        # CONNECT TO MYSQL
        # --------------------------------------

        db = mysql.connector.connect(
            host="localhost",
            port=3306,
            user="root",
            password="3012",
            database="smart_lost_found",
            connection_timeout=10
        )

        if not db.is_connected():
            print()
            print("======================================")
            print("DATABASE CONNECTION FAILED")
            print("======================================")
            return

        print()
        print("======================================")
        print("DATABASE CONNECTION SUCCESSFUL")
        print("======================================")

        cursor = db.cursor()

        # --------------------------------------
        # CHECK DATABASE
        # --------------------------------------

        cursor.execute("SELECT DATABASE()")

        database_name = cursor.fetchone()

        if database_name:
            print("DATABASE:", database_name[0])

        # --------------------------------------
        # CHECK USERS TABLE
        # --------------------------------------

        cursor.execute("SELECT COUNT(*) FROM users")

        result = cursor.fetchone()

        total_users = result[0] if result else 0

        print("TOTAL USERS:", total_users)

        # --------------------------------------
        # SHOW REGISTERED USERS
        # --------------------------------------

        cursor.execute(
            """
            SELECT id, name, email, role
            FROM users
            ORDER BY id ASC
            """
        )

        users = cursor.fetchall()

        print()
        print("REGISTERED USERS:")
        print("--------------------------------------")

        if users:

            for user in users:

                print(
                    "ID:", user[0],
                    "| Name:", user[1],
                    "| Email:", user[2],
                    "| Role:", user[3]
                )

        else:

            print("No registered users found.")

        print("--------------------------------------")

        # --------------------------------------
        # CHECK LOST ITEMS TABLE
        # --------------------------------------

        cursor.execute("SELECT COUNT(*) FROM lost_items")

        result = cursor.fetchone()

        total_lost = result[0] if result else 0

        print("TOTAL LOST REPORTS:", total_lost)

        # --------------------------------------
        # CHECK FOUND ITEMS TABLE
        # --------------------------------------

        cursor.execute("SELECT COUNT(*) FROM found_items")

        result = cursor.fetchone()

        total_found = result[0] if result else 0

        print("TOTAL FOUND REPORTS:", total_found)

        # --------------------------------------
        # CHECK CLAIMS TABLE
        # --------------------------------------

        cursor.execute("SELECT COUNT(*) FROM claims")

        result = cursor.fetchone()

        total_claims = result[0] if result else 0

        print("TOTAL CLAIMS:", total_claims)

        print()
        print("======================================")
        print("DATABASE TEST COMPLETED SUCCESSFULLY")
        print("======================================")

    except Error as e:

        print()
        print("======================================")
        print("DATABASE CONNECTION FAILED")
        print("======================================")
        print("ERROR:", repr(e))
        print("======================================")

    except Exception as e:

        print()
        print("======================================")
        print("DATABASE TEST FAILED")
        print("======================================")
        print("ERROR:", repr(e))
        print("======================================")

    finally:

        if cursor is not None:

            try:
                cursor.close()
            except Exception:
                pass

        if db is not None:

            try:
                if db.is_connected():
                    db.close()
            except Exception:
                pass


if __name__ == "__main__":
    test_database()