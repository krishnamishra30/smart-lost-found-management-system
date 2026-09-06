from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

import os
import re
import tempfile

import mysql.connector
from mysql.connector import Error

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from difflib import SequenceMatcher


app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "smart_lost_found_secret_key_2026"
)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

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
    "3012"
)

DB_NAME = os.environ.get(
    "DB_NAME",
    "smart_lost_found"
).strip()

DB_SSL_CA = os.environ.get(
    "DB_SSL_CA",
    ""
).strip()


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db_connection():

    is_remote_database = (
        DB_HOST.lower() not in [
            "",
            "localhost",
            "127.0.0.1"
        ]
    )

    config = {
        "host": DB_HOST,
        "port": DB_PORT,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "database": DB_NAME,
        "connection_timeout": 20,
        "autocommit": False,
        "use_pure": True
    }

    if not is_remote_database:

        print(
            "DATABASE MODE: LOCAL MYSQL"
        )

    else:

        print(
            "DATABASE MODE: REMOTE MYSQL"
        )

        config["ssl_disabled"] = False

        config["tls_versions"] = [
            "TLSv1.2",
            "TLSv1.3"
        ]

        if DB_SSL_CA:

            ssl_ca = DB_SSL_CA.strip()

            if "BEGIN CERTIFICATE" in ssl_ca:

                temp_file = tempfile.NamedTemporaryFile(
                    mode="w",
                    suffix=".pem",
                    delete=False,
                    encoding="utf-8"
                )

                temp_file.write(ssl_ca)
                temp_file.close()

                config["ssl_ca"] = temp_file.name

            else:

                config["ssl_ca"] = ssl_ca

            config["ssl_verify_cert"] = True
            config["ssl_verify_identity"] = True

        else:

            config["ssl_verify_cert"] = False
            config["ssl_verify_identity"] = False

    print(
        "DATABASE CONFIG:",
        {
            "host": DB_HOST,
            "port": DB_PORT,
            "user": DB_USER,
            "database": DB_NAME,
            "remote": is_remote_database,
            "ssl_enabled": is_remote_database
        }
    )

    try:

        connection = mysql.connector.connect(
            **config
        )

        if connection.is_connected():

            print(
                "DATABASE CONNECTION: SUCCESS"
            )

            return connection

        raise ConnectionError(
            "Database connection was not established."
        )

    except Error as e:

        print(
            "MYSQL CONNECTION ERROR:",
            repr(e)
        )

        raise

    except Exception as e:

        print(
            "DATABASE CONNECTION ERROR:",
            repr(e)
        )

        raise


# ============================================================
# HELPERS
# ============================================================

def is_logged_in():

    return "user_id" in session


def login_required():

    if not is_logged_in():

        flash(
            "Please login first.",
            "error"
        )

        return False

    return True


def admin_required():

    if not is_logged_in():

        flash(
            "Please login first.",
            "error"
        )

        return False

    if session.get("user_role") != "admin":

        flash(
            "Admin access required.",
            "error"
        )

        return False

    return True


def similarity(text1, text2):

    if not text1 or not text2:

        return 0

    text1 = str(text1).lower().strip()
    text2 = str(text2).lower().strip()

    return SequenceMatcher(
        None,
        text1,
        text2
    ).ratio()


def calculate_match(
    lost_item,
    found_item
):

    category_score = similarity(
        lost_item.get("category"),
        found_item.get("category")
    )

    name_score = similarity(
        lost_item.get("item_name"),
        found_item.get("item_name")
    )

    description_score = similarity(
        lost_item.get("description"),
        found_item.get("description")
    )

    location_score = similarity(
        lost_item.get("lost_location"),
        found_item.get("found_location")
    )

    color_score = similarity(
        lost_item.get("color"),
        found_item.get("color")
    )

    total_score = (
        category_score * 25
        + name_score * 25
        + description_score * 20
        + location_score * 20
        + color_score * 10
    )

    return round(
        total_score,
        2
    )


# ============================================================
# HOME
# ============================================================

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


# ============================================================
# ABOUT
# ============================================================

@app.route("/about")
def about():

    return render_template(
        "about.html"
    )


# ============================================================
# CONTACT
# ============================================================

@app.route("/contact")
def contact():

    return render_template(
        "contact.html"
    )


# ============================================================
# REGISTER
# ============================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if not name or not email or not password:

            flash(
                "All fields are required.",
                "error"
            )

            return render_template(
                "register.html"
            )

        if len(name) < 2:

            flash(
                "Please enter a valid name.",
                "error"
            )

            return render_template(
                "register.html"
            )

        email_pattern = (
            r"^[A-Za-z0-9._%+-]+@"
            r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
        )

        if not re.match(
            email_pattern,
            email
        ):

            flash(
                "Please enter a valid email address.",
                "error"
            )

            return render_template(
                "register.html"
            )

        if len(password) < 6:

            flash(
                "Password must be at least 6 characters.",
                "error"
            )

            return render_template(
                "register.html"
            )

        connection = None
        cursor = None

        try:

            connection = get_db_connection()

            cursor = connection.cursor(
                dictionary=True
            )

            cursor.execute(
                """
                SELECT id
                FROM users
                WHERE email = %s
                LIMIT 1
                """,
                (email,)
            )

            existing_user = cursor.fetchone()

            if existing_user:

                flash(
                    "Email is already registered.",
                    "error"
                )

                return render_template(
                    "register.html"
                )

            hashed_password = generate_password_hash(
                password
            )

            cursor.execute(
                """
                INSERT INTO users
                (
                    name,
                    email,
                    password,
                    role
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    name,
                    email,
                    hashed_password,
                    "user"
                )
            )

            connection.commit()

            flash(
                "Registration successful. Please login.",
                "success"
            )

            return redirect(
                url_for("login")
            )

        except Error as e:

            if connection:
                connection.rollback()

            print(
                "REGISTER DATABASE ERROR:",
                repr(e)
            )

            flash(
                "Database error. Please try again.",
                "error"
            )

            return render_template(
                "register.html"
            )

        except Exception as e:

            if connection:
                connection.rollback()

            print(
                "REGISTER ERROR:",
                repr(e)
            )

            flash(
                "Something went wrong. Please try again.",
                "error"
            )

            return render_template(
                "register.html"
            )

        finally:

            if cursor:

                cursor.close()

            if connection and connection.is_connected():

                connection.close()

    return render_template(
        "register.html"
    )


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if not email or not password:

            flash(
                "Email and password are required.",
                "error"
            )

            return render_template(
                "login.html"
            )

        connection = None
        cursor = None

        try:

            connection = get_db_connection()

            cursor = connection.cursor(
                dictionary=True
            )

            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    email,
                    password,
                    role
                FROM users
                WHERE email = %s
                LIMIT 1
                """,
                (email,)
            )

            user = cursor.fetchone()

            if user is None:

                flash(
                    "Invalid email or password.",
                    "error"
                )

                return render_template(
                    "login.html"
                )

            if not check_password_hash(
                user["password"],
                password
            ):

                flash(
                    "Invalid email or password.",
                    "error"
                )

                return render_template(
                    "login.html"
                )

            session.clear()

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_email"] = user["email"]
            session["user_role"] = user["role"]

            flash(
                "Login successful.",
                "success"
            )

            return redirect(
                url_for("dashboard")
            )

        except Error as e:

            print(
                "LOGIN DATABASE ERROR:",
                repr(e)
            )

            flash(
                "Database error. Please try again.",
                "error"
            )

            return render_template(
                "login.html"
            )

        except Exception as e:

            print(
                "LOGIN ERROR:",
                repr(e)
            )

            flash(
                "Something went wrong. Please try again.",
                "error"
            )

            return render_template(
                "login.html"
            )

        finally:

            if cursor:

                cursor.close()

            if connection and connection.is_connected():

                connection.close()

    return render_template(
        "login.html"
    )


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
def dashboard():

    if not login_required():

        return redirect(
            url_for("login")
        )

    connection = None
    cursor = None

    stats = {
        "lost": 0,
        "found": 0,
        "claims": 0,
        "matches": 0
    }

    try:

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        user_id = session["user_id"]

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM lost_items
            WHERE user_id = %s
            """,
            (user_id,)
        )

        result = cursor.fetchone()

        stats["lost"] = (
            result["total"]
            if result
            else 0
        )

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM found_items
            WHERE user_id = %s
            """,
            (user_id,)
        )

        result = cursor.fetchone()

        stats["found"] = (
            result["total"]
            if result
            else 0
        )

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM claims
            WHERE claimant_id = %s
            """,
            (user_id,)
        )

        result = cursor.fetchone()

        stats["claims"] = (
            result["total"]
            if result
            else 0
        )

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM lost_items
            WHERE user_id = %s
            AND status = 'Lost'
            """,
            (user_id,)
        )

        result = cursor.fetchone()

        stats["matches"] = (
            result["total"]
            if result
            else 0
        )

    except Exception as e:

        print(
            "DASHBOARD ERROR:",
            repr(e)
        )

    finally:

        if cursor:

            cursor.close()

        if connection and connection.is_connected():

            connection.close()

    return render_template(
        "dashboard.html",
        stats=stats
    )


# ============================================================
# REPORT LOST ITEM
# ============================================================

@app.route(
    "/report-lost",
    methods=["GET", "POST"]
)
def report_lost():

    if not login_required():

        return redirect(
            url_for("login")
        )

    if request.method == "POST":

        item_name = request.form.get(
            "item_name",
            ""
        ).strip()

        category = request.form.get(
            "category",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        lost_location = request.form.get(
            "lost_location",
            ""
        ).strip()

        lost_date = request.form.get(
            "lost_date",
            ""
        ).strip()

        color = request.form.get(
            "color",
            ""
        ).strip()

        identification_details = request.form.get(
            "identification_details",
            ""
        ).strip()

        if not all(
            [
                item_name,
                category,
                description,
                lost_location,
                lost_date
            ]
        ):

            flash(
                "Please fill all required fields.",
                "error"
            )

            return render_template(
                "report_lost.html"
            )

        image_filename = None

        uploaded_file = request.files.get(
            "image"
        )

        if uploaded_file and uploaded_file.filename:

            upload_folder = os.path.join(
                app.root_path,
                "uploads"
            )

            os.makedirs(
                upload_folder,
                exist_ok=True
            )

            safe_name = re.sub(
                r"[^A-Za-z0-9_.-]",
                "_",
                uploaded_file.filename
            )

            image_filename = safe_name

            uploaded_file.save(
                os.path.join(
                    upload_folder,
                    image_filename
                )
            )

        connection = None
        cursor = None

        try:

            connection = get_db_connection()

            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO lost_items
                (
                    user_id,
                    item_name,
                    category,
                    description,
                    lost_location,
                    lost_date,
                    color,
                    identification_details,
                    image,
                    status
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    session["user_id"],
                    item_name,
                    category,
                    description,
                    lost_location,
                    lost_date,
                    color,
                    identification_details,
                    image_filename,
                    "Lost"
                )
            )

            connection.commit()

            flash(
                "Lost item reported successfully.",
                "success"
            )

            return redirect(
                url_for("my_reports")
            )

        except Error as e:

            if connection:
                connection.rollback()

            print(
                "REPORT LOST DATABASE ERROR:",
                repr(e)
            )

            flash(
                "Database error. Please try again.",
                "error"
            )

        except Exception as e:

            if connection:
                connection.rollback()

            print(
                "REPORT LOST ERROR:",
                repr(e)
            )

            flash(
                "Something went wrong. Please try again.",
                "error"
            )

        finally:

            if cursor:

                cursor.close()

            if connection and connection.is_connected():

                connection.close()

    return render_template(
        "report_lost.html"
    )


# ============================================================
# REPORT FOUND ITEM
# ============================================================

@app.route(
    "/report-found",
    methods=["GET", "POST"]
)
def report_found():

    if not login_required():

        return redirect(
            url_for("login")
        )

    if request.method == "POST":

        item_name = request.form.get(
            "item_name",
            ""
        ).strip()

        category = request.form.get(
            "category",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        found_location = request.form.get(
            "found_location",
            ""
        ).strip()

        found_date = request.form.get(
            "found_date",
            ""
        ).strip()

        color = request.form.get(
            "color",
            ""
        ).strip()

        identification_details = request.form.get(
            "identification_details",
            ""
        ).strip()

        if not all(
            [
                item_name,
                category,
                description,
                found_location,
                found_date
            ]
        ):

            flash(
                "Please fill all required fields.",
                "error"
            )

            return render_template(
                "report_found.html"
            )

        image_filename = None

        uploaded_file = request.files.get(
            "image"
        )

        if uploaded_file and uploaded_file.filename:

            upload_folder = os.path.join(
                app.root_path,
                "uploads"
            )

            os.makedirs(
                upload_folder,
                exist_ok=True
            )

            safe_name = re.sub(
                r"[^A-Za-z0-9_.-]",
                "_",
                uploaded_file.filename
            )

            image_filename = safe_name

            uploaded_file.save(
                os.path.join(
                    upload_folder,
                    image_filename
                )
            )

        connection = None
        cursor = None

        try:

            connection = get_db_connection()

            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO found_items
                (
                    user_id,
                    item_name,
                    category,
                    description,
                    found_location,
                    found_date,
                    color,
                    identification_details,
                    image,
                    status
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    session["user_id"],
                    item_name,
                    category,
                    description,
                    found_location,
                    found_date,
                    color,
                    identification_details,
                    image_filename,
                    "Found"
                )
            )

            connection.commit()

            flash(
                "Found item reported successfully.",
                "success"
            )

            return redirect(
                url_for("search")
            )

        except Error as e:

            if connection:
                connection.rollback()

            print(
                "REPORT FOUND DATABASE ERROR:",
                repr(e)
            )

            flash(
                "Database error. Please try again.",
                "error"
            )

        except Exception as e:

            if connection:
                connection.rollback()

            print(
                "REPORT FOUND ERROR:",
                repr(e)
            )

            flash(
                "Something went wrong. Please try again.",
                "error"
            )

        finally:

            if cursor:

                cursor.close()

            if connection and connection.is_connected():

                connection.close()

    return render_template(
        "report_found.html"
    )


# ============================================================
# SEARCH
# ============================================================

@app.route("/search")
def search():

    if not login_required():

        return redirect(
            url_for("login")
        )

    query = request.args.get(
        "q",
        ""
    ).strip()

    category = request.args.get(
        "category",
        ""
    ).strip()

    item_type = request.args.get(
        "type",
        "all"
    ).strip().lower()

    connection = None
    cursor = None

    lost_items = []
    found_items = []

    try:

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        search_value = f"%{query}%"

        if item_type in ["all", "lost"]:

            if query and category:

                cursor.execute(
                    """
                    SELECT
                        l.*,
                        u.name AS reporter_name
                    FROM lost_items l
                    JOIN users u
                        ON l.user_id = u.id
                    WHERE
                        (
                            l.item_name LIKE %s
                            OR l.description LIKE %s
                            OR l.lost_location LIKE %s
                        )
                        AND l.category = %s
                    ORDER BY l.created_at DESC
                    """,
                    (
                        search_value,
                        search_value,
                        search_value,
                        category
                    )
                )

            elif query:

                cursor.execute(
                    """
                    SELECT
                        l.*,
                        u.name AS reporter_name
                    FROM lost_items l
                    JOIN users u
                        ON l.user_id = u.id
                    WHERE
                        l.item_name LIKE %s
                        OR l.description LIKE %s
                        OR l.lost_location LIKE %s
                    ORDER BY l.created_at DESC
                    """,
                    (
                        search_value,
                        search_value,
                        search_value
                    )
                )

            elif category:

                cursor.execute(
                    """
                    SELECT
                        l.*,
                        u.name AS reporter_name
                    FROM lost_items l
                    JOIN users u
                        ON l.user_id = u.id
                    WHERE l.category = %s
                    ORDER BY l.created_at DESC
                    """,
                    (category,)
                )

            else:

                cursor.execute(
                    """
                    SELECT
                        l.*,
                        u.name AS reporter_name
                    FROM lost_items l
                    JOIN users u
                        ON l.user_id = u.id
                    ORDER BY l.created_at DESC
                    """
                )

            lost_items = cursor.fetchall()

        if item_type in ["all", "found"]:

            if query and category:

                cursor.execute(
                    """
                    SELECT
                        f.*,
                        u.name AS reporter_name
                    FROM found_items f
                    JOIN users u
                        ON f.user_id = u.id
                    WHERE
                        (
                            f.item_name LIKE %s
                            OR f.description LIKE %s
                            OR f.found_location LIKE %s
                        )
                        AND f.category = %s
                    ORDER BY f.created_at DESC
                    """,
                    (
                        search_value,
                        search_value,
                        search_value,
                        category
                    )
                )

            elif query:

                cursor.execute(
                    """
                    SELECT
                        f.*,
                        u.name AS reporter_name
                    FROM found_items f
                    JOIN users u
                        ON f.user_id = u.id
                    WHERE
                        f.item_name LIKE %s
                        OR f.description LIKE %s
                        OR f.found_location LIKE %s
                    ORDER BY f.created_at DESC
                    """,
                    (
                        search_value,
                        search_value,
                        search_value
                    )
                )

            elif category:

                cursor.execute(
                    """
                    SELECT
                        f.*,
                        u.name AS reporter_name
                    FROM found_items f
                    JOIN users u
                        ON f.user_id = u.id
                    WHERE f.category = %s
                    ORDER BY f.created_at DESC
                    """,
                    (category,)
                )

            else:

                cursor.execute(
                    """
                    SELECT
                        f.*,
                        u.name AS reporter_name
                    FROM found_items f
                    JOIN users u
                        ON f.user_id = u.id
                    ORDER BY f.created_at DESC
                    """
                )

            found_items = cursor.fetchall()

    except Exception as e:

        print(
            "SEARCH ERROR:",
            repr(e)
        )

        flash(
            "Unable to load search results.",
            "error"
        )

    finally:

        if cursor:

            cursor.close()

        if connection and connection.is_connected():

            connection.close()

    return render_template(
        "search.html",
        lost_items=lost_items,
        found_items=found_items,
        query=query,
        category=category,
        item_type=item_type
    )


# ============================================================
# ITEM DETAILS
# ============================================================

@app.route(
    "/item/<string:item_type>/<int:item_id>"
)
def item_details(
    item_type,
    item_id
):

    if not login_required():

        return redirect(
            url_for("login")
        )

    item_type = item_type.lower()

    if item_type not in [
        "lost",
        "found"
    ]:

        flash(
            "Invalid item type.",
            "error"
        )

        return redirect(
            url_for("search")
        )

    connection = None
    cursor = None

    item = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        if item_type == "lost":

            cursor.execute(
                """
                SELECT
                    l.*,
                    u.name AS reporter_name,
                    u.email AS reporter_email
                FROM lost_items l
                JOIN users u
                    ON l.user_id = u.id
                WHERE l.id = %s
                LIMIT 1
                """,
                (item_id,)
            )

        else:

            cursor.execute(
                """
                SELECT
                    f.*,
                    u.name AS reporter_name,
                    u.email AS reporter_email
                FROM found_items f
                JOIN users u
                    ON f.user_id = u.id
                WHERE f.id = %s
                LIMIT 1
                """,
                (item_id,)
            )

        item = cursor.fetchone()

        if not item:

            flash(
                "Item not found.",
                "error"
            )

            return redirect(
                url_for("search")
            )

    except Exception as e:

        print(
            "ITEM DETAILS ERROR:",
            repr(e)
        )

        flash(
            "Unable to load item.",
            "error"
        )

        return redirect(
            url_for("search")
        )

    finally:

        if cursor:

            cursor.close()

        if connection and connection.is_connected():

            connection.close()

    return render_template(
        "item_details.html",
        item=item,
        item_type=item_type
    )


# ============================================================
# SMART MATCHING
# ============================================================

@app.route("/matches")
def matches():

    if not login_required():

        return redirect(
            url_for("login")
        )

    connection = None
    cursor = None

    matches_data = []

    try:

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        user_id = session["user_id"]

        cursor.execute(
            """
            SELECT *
            FROM lost_items
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (user_id,)
        )

        lost_items = cursor.fetchall()

        cursor.execute(
            """
            SELECT
                f.*,
                u.name AS reporter_name
            FROM found_items f
            JOIN users u
                ON f.user_id = u.id
            WHERE f.status = 'Found'
            ORDER BY f.created_at DESC
            """
        )

        found_items = cursor.fetchall()

        for lost_item in lost_items:

            for found_item in found_items:

                score = calculate_match(
                    lost_item,
                    found_item
                )

                if score >= 35:

                    matches_data.append(
                        {
                            "lost_item": lost_item,
                            "found_item": found_item,
                            "score": score
                        }
                    )

        matches_data.sort(
            key=lambda x: x["score"],
            reverse=True
        )

    except Exception as e:

        print(
            "MATCHES ERROR:",
            repr(e)
        )

        flash(
            "Unable to calculate smart matches.",
            "error"
        )

    finally:

        if cursor:

            cursor.close()

        if connection and connection.is_connected():

            connection.close()

    return render_template(
        "matches.html",
        matches=matches_data
    )


# ============================================================
# MY REPORTS
# ============================================================

@app.route("/my-reports")
def my_reports():

    if not login_required():

        return redirect(
            url_for("login")
        )

    connection = None
    cursor = None

    lost_items = []
    found_items = []

    try:

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        user_id = session["user_id"]

        cursor.execute(
            """
            SELECT *
            FROM lost_items
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (user_id,)
        )

        lost_items = cursor.fetchall()

        cursor.execute(
            """
            SELECT *
            FROM found_items
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (user_id,)
        )

        found_items = cursor.fetchall()

    except Exception as e:

        print(
            "MY REPORTS ERROR:",
            repr(e)
        )

        flash(
            "Unable to load your reports.",
            "error"
        )

    finally:

        if cursor:

            cursor.close()

        if connection and connection.is_connected():

            connection.close()

    return render_template(
        "my_reports.html",
        lost_items=lost_items,
        found_items=found_items
    )


# ============================================================
# CLAIM ITEM
# ============================================================

@app.route(
    "/claim/<int:found_item_id>/<int:lost_item_id>",
    methods=["GET", "POST"]
)
def claim(
    found_item_id,
    lost_item_id
):

    if not login_required():

        return redirect(
            url_for("login")
        )

    connection = None
    cursor = None

    found_item = None
    lost_item = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT *
            FROM found_items
            WHERE id = %s
            LIMIT 1
            """,
            (found_item_id,)
        )

        found_item = cursor.fetchone()

        cursor.execute(
            """
            SELECT *
            FROM lost_items
            WHERE id = %s
            LIMIT 1
            """,
            (lost_item_id,)
        )

        lost_item = cursor.fetchone()

        if not found_item or not lost_item:

            flash(
                "Item not found.",
                "error"
            )

            return redirect(
                url_for("matches")
            )

        if request.method == "POST":

            claim_message = request.form.get(
                "claim_message",
                ""
            ).strip()

            if not claim_message:

                flash(
                    "Claim message is required.",
                    "error"
                )

                return render_template(
                    "claim.html",
                    found_item=found_item,
                    lost_item=lost_item
                )

            cursor.execute(
                """
                SELECT id
                FROM claims
                WHERE
                    found_item_id = %s
                    AND claimant_id = %s
                    AND lost_item_id = %s
                LIMIT 1
                """,
                (
                    found_item_id,
                    session["user_id"],
                    lost_item_id
                )
            )

            existing_claim = cursor.fetchone()

            if existing_claim:

                flash(
                    "You have already submitted a claim for this item.",
                    "error"
                )

                return redirect(
                    url_for("my_claims")
                )

            cursor.execute(
                """
                INSERT INTO claims
                (
                    found_item_id,
                    claimant_id,
                    lost_item_id,
                    claim_message,
                    status
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    found_item_id,
                    session["user_id"],
                    lost_item_id,
                    claim_message,
                    "Pending"
                )
            )

            connection.commit()

            flash(
                "Claim submitted successfully.",
                "success"
            )

            return redirect(
                url_for("my_claims")
            )

    except Error as e:

        if connection:
            connection.rollback()

        print(
            "CLAIM DATABASE ERROR:",
            repr(e)
        )

        flash(
            "Unable to submit claim.",
            "error"
        )

    except Exception as e:

        if connection:
            connection.rollback()

        print(
            "CLAIM ERROR:",
            repr(e)
        )

        flash(
            "Something went wrong.",
            "error"
        )

    finally:

        if cursor:

            cursor.close()

        if connection and connection.is_connected():

            connection.close()

    return render_template(
        "claim.html",
        found_item=found_item,
        lost_item=lost_item
    )


# ============================================================
# MY CLAIMS
# ============================================================

@app.route("/my-claims")
def my_claims():

    if not login_required():

        return redirect(
            url_for("login")
        )

    connection = None
    cursor = None

    claims_data = []

    try:

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT
                c.*,

                f.item_name AS found_item_name,
                f.category AS found_category,
                f.found_location,
                f.found_date,

                l.item_name AS lost_item_name,
                l.category AS lost_category,
                l.lost_location,
                l.lost_date,

                u.name AS claimant_name,
                u.email AS claimant_email

            FROM claims c

            JOIN found_items f
                ON c.found_item_id = f.id

            JOIN lost_items l
                ON c.lost_item_id = l.id

            JOIN users u
                ON c.claimant_id = u.id

            WHERE c.claimant_id = %s

            ORDER BY c.created_at DESC
            """,
            (session["user_id"],)
        )

        claims_data = cursor.fetchall()

    except Exception as e:

        print(
            "MY CLAIMS ERROR:",
            repr(e)
        )

        flash(
            "Unable to load your claims.",
            "error"
        )

    finally:

        if cursor:

            cursor.close()

        if connection and connection.is_connected():

            connection.close()

    return render_template(
        "my_claims.html",
        claims=claims_data
    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.route("/admin-dashboard")
def admin_dashboard():

    if not admin_required():

        return redirect(
            url_for("dashboard")
        )

    connection = None
    cursor = None

    stats = {
        "users": 0,
        "lost": 0,
        "found": 0,
        "claims": 0,
        "pending_claims": 0
    }

    try:

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM users
            """
        )

        result = cursor.fetchone()

        stats["users"] = (
            result["total"]
            if result
            else 0
        )

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM lost_items
            """
        )

        result = cursor.fetchone()

        stats["lost"] = (
            result["total"]
            if result
            else 0
        )

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM found_items
            """
        )

        result = cursor.fetchone()

        stats["found"] = (
            result["total"]
            if result
            else 0
        )

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM claims
            """
        )

        result = cursor.fetchone()

        stats["claims"] = (
            result["total"]
            if result
            else 0
        )

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM claims
            WHERE status = 'Pending'
            """
        )

        result = cursor.fetchone()

        stats["pending_claims"] = (
            result["total"]
            if result
            else 0
        )

    except Exception as e:

        print(
            "ADMIN DASHBOARD ERROR:",
            repr(e)
        )

        flash(
            "Unable to load admin dashboard.",
            "error"
        )

    finally:

        if cursor:

            cursor.close()

        if connection and connection.is_connected():

            connection.close()

    return render_template(
        "admin_dashboard.html",
        stats=stats
    )


# ============================================================
# ADMIN CLAIMS
# ============================================================

@app.route("/admin/claims")
def admin_claims():

    if not admin_required():

        return redirect(
            url_for("dashboard")
        )

    connection = None
    cursor = None

    claims_data = []

    try:

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT
                c.*,

                f.item_name AS found_item_name,
                f.category AS found_category,
                f.found_location,
                f.found_date,

                l.item_name AS lost_item_name,
                l.category AS lost_category,
                l.lost_location,
                l.lost_date,

                u.name AS claimant_name,
                u.email AS claimant_email

            FROM claims c

            JOIN found_items f
                ON c.found_item_id = f.id

            JOIN lost_items l
                ON c.lost_item_id = l.id

            JOIN users u
                ON c.claimant_id = u.id

            ORDER BY c.created_at DESC
            """
        )

        claims_data = cursor.fetchall()

    except Exception as e:

        print(
            "ADMIN CLAIMS ERROR:",
            repr(e)
        )

        flash(
            "Unable to load claims.",
            "error"
        )

    finally:

        if cursor:

            cursor.close()

        if connection and connection.is_connected():

            connection.close()

    return render_template(
        "admin_claims.html",
        claims=claims_data
    )


# ============================================================
# ADMIN UPDATE CLAIM
# ============================================================

@app.route(
    "/admin/claim/<int:claim_id>/update",
    methods=["POST"]
)
def update_claim(
    claim_id
):

    if not admin_required():

        return redirect(
            url_for("dashboard")
        )

    status = request.form.get(
        "status",
        ""
    ).strip()

    admin_note = request.form.get(
        "admin_note",
        ""
    ).strip()

    allowed_statuses = [
        "Pending",
        "Approved",
        "Rejected"
    ]

    if status not in allowed_statuses:

        flash(
            "Invalid claim status.",
            "error"
        )

        return redirect(
            url_for("admin_claims")
        )

    connection = None
    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE claims
            SET
                status = %s,
                admin_note = %s
            WHERE id = %s
            """,
            (
                status,
                admin_note,
                claim_id
            )
        )

        connection.commit()

        flash(
            "Claim status updated successfully.",
            "success"
        )

    except Error as e:

        if connection:
            connection.rollback()

        print(
            "UPDATE CLAIM DATABASE ERROR:",
            repr(e)
        )

        flash(
            "Unable to update claim.",
            "error"
        )

    except Exception as e:

        if connection:
            connection.rollback()

        print(
            "UPDATE CLAIM ERROR:",
            repr(e)
        )

        flash(
            "Something went wrong.",
            "error"
        )

    finally:

        if cursor:

            cursor.close()

        if connection and connection.is_connected():

            connection.close()

    return redirect(
        url_for("admin_claims")
    )


# ============================================================
# TRACK & STATUS
# ============================================================

@app.route("/track")
def track():

    if not login_required():

        return redirect(
            url_for("login")
        )

    connection = None
    cursor = None

    lost_items = []
    found_items = []
    claims_data = []

    try:

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        user_id = session["user_id"]

        cursor.execute(
            """
            SELECT *
            FROM lost_items
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (user_id,)
        )

        lost_items = cursor.fetchall()

        cursor.execute(
            """
            SELECT *
            FROM found_items
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (user_id,)
        )

        found_items = cursor.fetchall()

        cursor.execute(
            """
            SELECT
                c.*,
                f.item_name AS found_item_name,
                l.item_name AS lost_item_name
            FROM claims c

            JOIN found_items f
                ON c.found_item_id = f.id

            JOIN lost_items l
                ON c.lost_item_id = l.id

            WHERE c.claimant_id = %s

            ORDER BY c.created_at DESC
            """,
            (user_id,)
        )

        claims_data = cursor.fetchall()

    except Exception as e:

        print(
            "TRACK ERROR:",
            repr(e)
        )

        flash(
            "Unable to load tracking information.",
            "error"
        )

    finally:

        if cursor:

            cursor.close()

        if connection and connection.is_connected():

            connection.close()

    return render_template(
        "track.html",
        lost_items=lost_items,
        found_items=found_items,
        claims=claims_data
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor()

        cursor.execute(
            "SELECT 1"
        )

        result = cursor.fetchone()

        print(
            "HEALTH CHECK: DATABASE CONNECTED"
        )

        return {
            "status": "ok",
            "application": "Smart Lost & Found Management System",
            "database": "connected",
            "test": result[0] if result else None
        }, 200

    except Error as e:

        print(
            "HEALTH CHECK MYSQL ERROR:",
            repr(e)
        )

        return {
            "status": "error",
            "application": "Smart Lost & Found Management System",
            "database": "unavailable"
        }, 503

    except Exception as e:

        print(
            "HEALTH CHECK ERROR:",
            repr(e)
        )

        return {
            "status": "error",
            "application": "Smart Lost & Found Management System",
            "database": "unavailable"
        }, 503

    finally:

        if cursor:

            cursor.close()

        if connection and connection.is_connected():

            connection.close()


# ============================================================
# HOW IT WORKS
# ============================================================

@app.route("/how-it-works")
def how_it_works():

    return render_template(
        "how_it_works.html"
    )


# ============================================================
# HELP & SUPPORT
# ============================================================

@app.route("/help")
def help_page():

    return render_template(
        "help.html"
    )


# ============================================================
# PRIVACY POLICY
# ============================================================

@app.route("/privacy")
def privacy():

    return render_template(
        "privacy.html"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out successfully.",
        "success"
    )

    return redirect(
        url_for("index")
    )


# ============================================================
# 404 ERROR
# ============================================================

@app.errorhandler(404)
def page_not_found(error):

    return render_template(
        "404.html"
    ), 404


# ============================================================
# 413 ERROR
# ============================================================

@app.errorhandler(413)
def request_entity_too_large(error):

    return (
        "File is too large. Maximum allowed size is 5 MB.",
        413
    )


# ============================================================
# 500 ERROR
# ============================================================

@app.errorhandler(500)
def internal_server_error(error):

    return render_template(
        "500.html"
    ), 500


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        use_reloader=False
    )