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


# =========================================================
# FLASK APP CONFIGURATION
# =========================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "smart_lost_found_secret_key_2026"
)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024


# =========================================================
# DATABASE CONFIGURATION
# =========================================================

DB_HOST = os.environ.get(
    "DB_HOST",
    "localhost"
).strip()

DB_PORT = int(
    os.environ.get(
        "DB_PORT",
        "3306"
    )
)

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


# =========================================================
# AIVEN / RENDER DATABASE CONNECTION
# =========================================================

def get_db_connection():

    config = {
        "host": DB_HOST,
        "port": DB_PORT,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "database": DB_NAME,
        "connection_timeout": 15,
        "autocommit": False
    }

    # -----------------------------------------------------
    # AIVEN SSL
    # -----------------------------------------------------

    if DB_HOST != "localhost" and DB_SSL_CA:

        ssl_ca = DB_SSL_CA.strip()

        # If environment variable contains the complete
        # certificate text, create a temporary CA file.
        if "BEGIN CERTIFICATE" in ssl_ca:

            ca_file = tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".pem",
                delete=False
            )

            ca_file.write(ssl_ca)
            ca_file.flush()
            ca_file.close()

            config["ssl_ca"] = ca_file.name
            config["ssl_verify_cert"] = True
            config["ssl_verify_identity"] = True

        else:

            # If DB_SSL_CA contains an actual file path.
            config["ssl_ca"] = ssl_ca
            config["ssl_verify_cert"] = True
            config["ssl_verify_identity"] = True

    elif DB_HOST != "localhost":

        # Aiven requires SSL.
        # Encrypted connection is enabled even when CA
        # certificate is not supplied.
        config["ssl_disabled"] = False
        config["ssl_verify_cert"] = False
        config["ssl_verify_identity"] = False

    print(
        "DATABASE CONFIG:",
        {
            "host": DB_HOST,
            "port": DB_PORT,
            "user": DB_USER,
            "database": DB_NAME,
            "ssl": DB_HOST != "localhost"
        }
    )

    try:

        connection = mysql.connector.connect(
            **config
        )

        if connection.is_connected():

            print(
                "DATABASE CONNECTION SUCCESSFUL"
            )

            return connection

        raise ConnectionError(
            "MySQL connection was not established."
        )

    except Error as e:

        print(
            "MYSQL CONNECTION ERROR:",
            repr(e)
        )

        raise


# =========================================================
# LOGIN REQUIRED
# =========================================================

def login_required():

    return "user_id" in session


# =========================================================
# ADMIN REQUIRED
# =========================================================

def admin_required():

    return (
        "user_id" in session
        and session.get("user_role") == "admin"
    )


# =========================================================
# SMART MATCHING
# =========================================================

def similarity(text1, text2):

    text1 = str(
        text1 or ""
    ).lower().strip()

    text2 = str(
        text2 or ""
    ).lower().strip()

    if not text1 or not text2:

        return 0

    return SequenceMatcher(
        None,
        text1,
        text2
    ).ratio()


def calculate_match(lost, found):

    score = 0

    # CATEGORY - 25%
    lost_category = str(
        lost.get("category", "")
    ).lower().strip()

    found_category = str(
        found.get("category", "")
    ).lower().strip()

    if (
        lost_category
        and found_category
        and lost_category == found_category
    ):

        score += 25

    # ITEM NAME - 25%
    name_score = similarity(
        lost.get("item_name"),
        found.get("item_name")
    )

    score += name_score * 25

    # DESCRIPTION - 20%
    description_score = similarity(
        lost.get("description"),
        found.get("description")
    )

    score += description_score * 20

    # LOCATION - 20%
    location_score = similarity(
        lost.get("lost_location"),
        found.get("found_location")
    )

    score += location_score * 20

    # COLOR - 10%
    color_score = similarity(
        lost.get("color"),
        found.get("color")
    )

    score += color_score * 10

    return round(score)


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# =========================================================
# ABOUT
# =========================================================

@app.route("/about")
def about():

    return render_template(
        "about.html"
    )


# =========================================================
# CONTACT
# =========================================================

@app.route("/contact")
def contact():

    return render_template(
        "contact.html"
    )


# =========================================================
# REGISTER
# =========================================================

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

        # REQUIRED FIELDS
        if not name or not email or not password:

            flash(
                "Please fill all required fields.",
                "error"
            )

            return render_template(
                "register.html"
            )

        # NAME VALIDATION
        if len(name) < 2:

            flash(
                "Name must contain at least 2 characters.",
                "error"
            )

            return render_template(
                "register.html"
            )

        if not re.match(
            r"^[A-Za-z .'-]+$",
            name
        ):

            flash(
                "Please enter a valid name.",
                "error"
            )

            return render_template(
                "register.html"
            )

        # EMAIL VALIDATION
        email_pattern = (
            r"^[A-Za-z0-9._%+-]+@"
            r"[A-Za-z0-9.-]+\."
            r"[A-Za-z]{2,}$"
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

        # PASSWORD VALIDATION
        if len(password) < 8:

            flash(
                "Password must be at least 8 characters.",
                "error"
            )

            return render_template(
                "register.html"
            )

        if not re.search(
            r"[A-Z]",
            password
        ):

            flash(
                "Password must contain an uppercase letter.",
                "error"
            )

            return render_template(
                "register.html"
            )

        if not re.search(
            r"[a-z]",
            password
        ):

            flash(
                "Password must contain a lowercase letter.",
                "error"
            )

            return render_template(
                "register.html"
            )

        if not re.search(
            r"[0-9]",
            password
        ):

            flash(
                "Password must contain a number.",
                "error"
            )

            return render_template(
                "register.html"
            )

        if not re.search(
            r"[^A-Za-z0-9]",
            password
        ):

            flash(
                "Password must contain a special character.",
                "error"
            )

            return render_template(
                "register.html"
            )

        db = None
        cursor = None

        try:

            db = get_db_connection()

            cursor = db.cursor(
                dictionary=True,
                buffered=True
            )

            # CHECK EMAIL
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

            # HASH PASSWORD
            hashed_password = generate_password_hash(
                password
            )

            # INSERT USER
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

            db.commit()

            print(
                "REGISTER SUCCESS:",
                email
            )

            flash(
                "Registration successful! Please login.",
                "success"
            )

            return redirect(
                url_for("login")
            )

        except Exception as e:

            print(
                "REGISTER DATABASE ERROR:",
                repr(e)
            )

            if db:

                try:
                    db.rollback()
                except Exception:
                    pass

            flash(
                "Database error. Please try again.",
                "error"
            )

            return render_template(
                "register.html"
            )

        finally:

            if cursor:

                try:
                    cursor.close()
                except Exception:
                    pass

            if db:

                try:
                    db.close()
                except Exception:
                    pass

    return render_template(
        "register.html"
    )


# =========================================================
# LOGIN
# =========================================================

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
                "Please enter email and password.",
                "error"
            )

            return render_template(
                "login.html"
            )

        db = None
        cursor = None

        try:

            db = get_db_connection()

            cursor = db.cursor(
                dictionary=True,
                buffered=True
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

            password_correct = check_password_hash(
                user["password"],
                password
            )

            if not password_correct:

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
                "Login successful!",
                "success"
            )

            return redirect(
                url_for("dashboard")
            )

        except Exception as e:

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

        finally:

            if cursor:

                try:
                    cursor.close()
                except Exception:
                    pass

            if db:

                try:
                    db.close()
                except Exception:
                    pass

    return render_template(
        "login.html"
    )


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if not login_required():

        return redirect(
            url_for("login")
        )

    db = None
    cursor = None

    total_reports = 0
    found_reports = 0
    possible_matches = 0
    successful_recoveries = 0

    try:

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True,
            buffered=True
        )

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM lost_items
            WHERE user_id = %s
            """,
            (session["user_id"],)
        )

        result = cursor.fetchone()

        lost_count = (
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
            (session["user_id"],)
        )

        result = cursor.fetchone()

        found_count = (
            result["total"]
            if result
            else 0
        )

        found_reports = found_count

        total_reports = (
            lost_count +
            found_count
        )

        cursor.execute(
            """
            SELECT
                id,
                item_name,
                category,
                description,
                lost_location,
                lost_date,
                color
            FROM lost_items
            WHERE user_id = %s
              AND status = 'Lost'
            """,
            (session["user_id"],)
        )

        user_lost_items = cursor.fetchall()

        cursor.execute(
            """
            SELECT
                id,
                item_name,
                category,
                description,
                found_location,
                found_date,
                color
            FROM found_items
            WHERE status = 'Found'
            """
        )

        all_found_items = cursor.fetchall()

        for lost in user_lost_items:

            for found in all_found_items:

                score = calculate_match(
                    lost,
                    found
                )

                if score >= 30:

                    possible_matches += 1

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM lost_items
            WHERE user_id = %s
              AND status IN ('Claimed', 'Returned')
            """,
            (session["user_id"],)
        )

        recovery = cursor.fetchone()

        successful_recoveries = (
            recovery["total"]
            if recovery
            else 0
        )

    except Exception as e:

        print(
            "DASHBOARD DATABASE ERROR:",
            repr(e)
        )

    finally:

        if cursor:

            try:
                cursor.close()
            except Exception:
                pass

        if db:

            try:
                db.close()
            except Exception:
                pass

    return render_template(
        "dashboard.html",
        name=session.get(
            "user_name",
            "User"
        ),
        email=session.get(
            "user_email",
            ""
        ),
        role=session.get(
            "user_role",
            "user"
        ),
        total_reports=total_reports,
        found_reports=found_reports,
        possible_matches=possible_matches,
        successful_recoveries=successful_recoveries
    )


# =========================================================
# REPORT LOST
# =========================================================

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

        if not item_name:

            flash(
                "Please enter item name.",
                "error"
            )

            return render_template(
                "report_lost.html"
            )

        if not category:

            flash(
                "Please select category.",
                "error"
            )

            return render_template(
                "report_lost.html"
            )

        if not description:

            flash(
                "Please enter description.",
                "error"
            )

            return render_template(
                "report_lost.html"
            )

        if not lost_location:

            flash(
                "Please enter lost location.",
                "error"
            )

            return render_template(
                "report_lost.html"
            )

        if not lost_date:

            flash(
                "Please select lost date.",
                "error"
            )

            return render_template(
                "report_lost.html"
            )

        db = None
        cursor = None

        try:

            db = get_db_connection()

            cursor = db.cursor()

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
                    'Lost'
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
                    identification_details
                )
            )

            db.commit()

            flash(
                "Lost item reported successfully!",
                "success"
            )

            return redirect(
                url_for("my_reports")
            )

        except Exception as e:

            print(
                "REPORT LOST ERROR:",
                repr(e)
            )

            if db:

                try:
                    db.rollback()
                except Exception:
                    pass

            flash(
                "Unable to save lost item.",
                "error"
            )

            return render_template(
                "report_lost.html"
            )

        finally:

            if cursor:

                try:
                    cursor.close()
                except Exception:
                    pass

            if db:

                try:
                    db.close()
                except Exception:
                    pass

    return render_template(
        "report_lost.html"
    )


# =========================================================
# REPORT FOUND
# =========================================================

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

        if not item_name:

            flash(
                "Please enter item name.",
                "error"
            )

            return render_template(
                "report_found.html"
            )

        if not category:

            flash(
                "Please select category.",
                "error"
            )

            return render_template(
                "report_found.html"
            )

        if not description:

            flash(
                "Please enter description.",
                "error"
            )

            return render_template(
                "report_found.html"
            )

        if not found_location:

            flash(
                "Please enter found location.",
                "error"
            )

            return render_template(
                "report_found.html"
            )

        if not found_date:

            flash(
                "Please select found date.",
                "error"
            )

            return render_template(
                "report_found.html"
            )

        db = None
        cursor = None

        try:

            db = get_db_connection()

            cursor = db.cursor()

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
                    'Found'
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
                    identification_details
                )
            )

            db.commit()

            flash(
                "Found item reported successfully!",
                "success"
            )

            return redirect(
                url_for("my_reports")
            )

        except Exception as e:

            print(
                "REPORT FOUND ERROR:",
                repr(e)
            )

            if db:

                try:
                    db.rollback()
                except Exception:
                    pass

            flash(
                "Unable to save found item.",
                "error"
            )

            return render_template(
                "report_found.html"
            )

        finally:

            if cursor:

                try:
                    cursor.close()
                except Exception:
                    pass

            if db:

                try:
                    db.close()
                except Exception:
                    pass

    return render_template(
        "report_found.html"
    )


# =========================================================
# SEARCH
# =========================================================

@app.route(
    "/search",
    methods=["GET", "POST"]
)
def search():

    if not login_required():

        return redirect(
            url_for("login")
        )

    keyword = request.args.get(
        "query",
        ""
    ).strip()

    category = request.args.get(
        "category",
        ""
    ).strip()

    item_type = request.args.get(
        "type",
        ""
    ).strip()

    location = request.args.get(
        "location",
        ""
    ).strip()

    results = []

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True,
            buffered=True
        )

        # LOST
        if item_type.lower() in [
            "",
            "lost"
        ]:

            lost_query = """
                SELECT
                    l.id,
                    l.item_name,
                    l.category,
                    l.description,
                    l.lost_location AS location,
                    l.lost_date AS item_date,
                    l.color,
                    l.identification_details,
                    l.status,
                    'Lost' AS report_type,
                    u.name AS reporter_name
                FROM lost_items l
                LEFT JOIN users u
                    ON l.user_id = u.id
                WHERE 1 = 1
            """

            lost_params = []

            if keyword:

                lost_query += """
                    AND (
                        l.item_name LIKE %s
                        OR l.category LIKE %s
                        OR l.description LIKE %s
                        OR l.identification_details LIKE %s
                        OR l.color LIKE %s
                    )
                """

                value = "%" + keyword + "%"

                lost_params.extend([
                    value,
                    value,
                    value,
                    value,
                    value
                ])

            if category:

                lost_query += """
                    AND LOWER(l.category) = LOWER(%s)
                """

                lost_params.append(
                    category
                )

            if location:

                lost_query += """
                    AND l.lost_location LIKE %s
                """

                lost_params.append(
                    "%" + location + "%"
                )

            cursor.execute(
                lost_query,
                tuple(lost_params)
            )

            lost_results = cursor.fetchall()

        else:

            lost_results = []

        # FOUND
        if item_type.lower() in [
            "",
            "found"
        ]:

            found_query = """
                SELECT
                    f.id,
                    f.item_name,
                    f.category,
                    f.description,
                    f.found_location AS location,
                    f.found_date AS item_date,
                    f.color,
                    f.identification_details,
                    f.status,
                    'Found' AS report_type,
                    u.name AS reporter_name
                FROM found_items f
                LEFT JOIN users u
                    ON f.user_id = u.id
                WHERE 1 = 1
            """

            found_params = []

            if keyword:

                found_query += """
                    AND (
                        f.item_name LIKE %s
                        OR f.category LIKE %s
                        OR f.description LIKE %s
                        OR f.identification_details LIKE %s
                        OR f.color LIKE %s
                    )
                """

                value = "%" + keyword + "%"

                found_params.extend([
                    value,
                    value,
                    value,
                    value,
                    value
                ])

            if category:

                found_query += """
                    AND LOWER(f.category) = LOWER(%s)
                """

                found_params.append(
                    category
                )

            if location:

                found_query += """
                    AND f.found_location LIKE %s
                """

                found_params.append(
                    "%" + location + "%"
                )

            cursor.execute(
                found_query,
                tuple(found_params)
            )

            found_results = cursor.fetchall()

        else:

            found_results = []

        results = (
            lost_results +
            found_results
        )

        results.sort(
            key=lambda x: str(
                x.get("item_date") or ""
            ),
            reverse=True
        )

    except Exception as e:

        print(
            "SEARCH ERROR:",
            repr(e)
        )

        flash(
            "Unable to search items. Please try again.",
            "error"
        )

    finally:

        if cursor:

            try:
                cursor.close()
            except Exception:
                pass

        if db:

            try:
                db.close()
            except Exception:
                pass

    return render_template(
        "search.html",
        results=results,
        query=keyword,
        keyword=keyword,
        category=category,
        location=location,
        type=item_type,
        item_type=item_type
    )


# =========================================================
# ITEM DETAILS
# =========================================================

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

    item_type = item_type.strip().lower()

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

    db = None
    cursor = None
    item = None

    try:

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True,
            buffered=True
        )

        if item_type == "lost":

            cursor.execute(
                """
                SELECT
                    l.id,
                    l.user_id,
                    l.item_name,
                    l.category,
                    l.description,
                    l.lost_location AS location,
                    l.lost_date AS item_date,
                    l.color,
                    l.identification_details,
                    l.image,
                    l.status,
                    l.created_at,
                    u.name AS reporter_name,
                    u.email AS reporter_email
                FROM lost_items l
                LEFT JOIN users u
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
                    f.id,
                    f.user_id,
                    f.item_name,
                    f.category,
                    f.description,
                    f.found_location AS location,
                    f.found_date AS item_date,
                    f.color,
                    f.identification_details,
                    f.image,
                    f.status,
                    f.created_at,
                    u.name AS reporter_name,
                    u.email AS reporter_email
                FROM found_items f
                LEFT JOIN users u
                    ON f.user_id = u.id
                WHERE f.id = %s
                LIMIT 1
                """,
                (item_id,)
            )

        item = cursor.fetchone()

    except Exception as e:

        print(
            "ITEM DETAILS ERROR:",
            repr(e)
        )

        flash(
            "Unable to load item details.",
            "error"
        )

    finally:

        if cursor:

            try:
                cursor.close()
            except Exception:
                pass

        if db:

            try:
                db.close()
            except Exception:
                pass

    if not item:

        flash(
            "Item not found.",
            "error"
        )

        return redirect(
            url_for("search")
        )

    return render_template(
        "item_details.html",
        item=item,
        item_type=item_type,
        name=session.get(
            "user_name",
            "User"
        )
    )


# =========================================================
# SMART MATCHES
# =========================================================

@app.route("/matches")
def matches():

    if not login_required():

        return redirect(
            url_for("login")
        )

    db = None
    cursor = None
    matches_list = []

    try:

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True,
            buffered=True
        )

        cursor.execute(
            """
            SELECT
                id,
                user_id,
                item_name,
                category,
                description,
                lost_location,
                lost_date,
                color,
                identification_details,
                status
            FROM lost_items
            WHERE user_id = %s
              AND status = 'Lost'
            ORDER BY created_at DESC
            """,
            (session["user_id"],)
        )

        lost_items = cursor.fetchall()

        cursor.execute(
            """
            SELECT
                id,
                user_id,
                item_name,
                category,
                description,
                found_location,
                found_date,
                color,
                identification_details,
                status
            FROM found_items
            WHERE status = 'Found'
            ORDER BY created_at DESC
            """
        )

        found_items = cursor.fetchall()

        for lost in lost_items:

            for found in found_items:

                score = calculate_match(
                    lost,
                    found
                )

                if score >= 30:

                    matches_list.append({
                        "score": score,
                        "lost": lost,
                        "found": found
                    })

        matches_list.sort(
            key=lambda item: item["score"],
            reverse=True
        )

    except Exception as e:

        print(
            "SMART MATCH ERROR:",
            repr(e)
        )

        if db:

            try:
                db.rollback()
            except Exception:
                pass

        flash(
            "Unable to load smart matches. Please try again.",
            "error"
        )

    finally:

        if cursor:

            try:
                cursor.close()
            except Exception:
                pass

        if db:

            try:
                db.close()
            except Exception:
                pass

    return render_template(
        "matches.html",
        matches=matches_list,
        name=session.get(
            "user_name",
            "User"
        )
    )


# =========================================================
# MY REPORTS
# =========================================================

@app.route("/my-reports")
def my_reports():

    if not login_required():

        return redirect(
            url_for("login")
        )

    db = None
    cursor = None
    reports = []

    try:

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True,
            buffered=True
        )

        cursor.execute(
            """
            SELECT
                id,
                item_name,
                category,
                description,
                lost_location AS location,
                lost_date AS item_date,
                color,
                status,
                'Lost' AS report_type
            FROM lost_items
            WHERE user_id = %s

            UNION ALL

            SELECT
                id,
                item_name,
                category,
                description,
                found_location AS location,
                found_date AS item_date,
                color,
                status,
                'Found' AS report_type
            FROM found_items
            WHERE user_id = %s

            ORDER BY item_date DESC
            """,
            (
                session["user_id"],
                session["user_id"]
            )
        )

        reports = cursor.fetchall()

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

            try:
                cursor.close()
            except Exception:
                pass

        if db:

            try:
                db.close()
            except Exception:
                pass

    return render_template(
        "my_reports.html",
        reports=reports
    )


# =========================================================
# CLAIM ITEM
# =========================================================

@app.route(
    "/claim/<int:found_item_id>/<int:lost_item_id>",
    methods=["GET", "POST"]
)
def claim_item(
    found_item_id,
    lost_item_id
):

    if not login_required():

        return redirect(
            url_for("login")
        )

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True,
            buffered=True
        )

        cursor.execute(
            """
            SELECT *
            FROM lost_items
            WHERE id = %s
              AND user_id = %s
            LIMIT 1
            """,
            (
                lost_item_id,
                session["user_id"]
            )
        )

        lost_item = cursor.fetchone()

        if not lost_item:

            flash(
                "Invalid lost item.",
                "error"
            )

            return redirect(
                url_for("matches")
            )

        cursor.execute(
            """
            SELECT *
            FROM found_items
            WHERE id = %s
              AND status = 'Found'
            LIMIT 1
            """,
            (found_item_id,)
        )

        found_item = cursor.fetchone()

        if not found_item:

            flash(
                "Found item is no longer available.",
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
                    "Please explain why this item belongs to you.",
                    "error"
                )

                return render_template(
                    "claim.html",
                    lost_item=lost_item,
                    found_item=found_item
                )

            if len(claim_message) < 10:

                flash(
                    "Claim explanation must contain at least 10 characters.",
                    "error"
                )

                return render_template(
                    "claim.html",
                    lost_item=lost_item,
                    found_item=found_item
                )

            cursor.execute(
                """
                SELECT id
                FROM claims
                WHERE found_item_id = %s
                  AND lost_item_id = %s
                  AND claimant_id = %s
                  AND status IN ('Pending', 'Approved')
                LIMIT 1
                """,
                (
                    found_item_id,
                    lost_item_id,
                    session["user_id"]
                )
            )

            existing_claim = cursor.fetchone()

            if existing_claim:

                flash(
                    "You already have an active claim for this item.",
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
                    'Pending'
                )
                """,
                (
                    found_item_id,
                    session["user_id"],
                    lost_item_id,
                    claim_message
                )
            )

            db.commit()

            flash(
                "Claim submitted successfully. Waiting for admin verification.",
                "success"
            )

            return redirect(
                url_for("my_claims")
            )

        return render_template(
            "claim.html",
            lost_item=lost_item,
            found_item=found_item
        )

    except Exception as e:

        print(
            "CLAIM ERROR:",
            repr(e)
        )

        if db:

            try:
                db.rollback()
            except Exception:
                pass

        flash(
            "Unable to process claim.",
            "error"
        )

        return redirect(
            url_for("matches")
        )

    finally:

        if cursor:

            try:
                cursor.close()
            except Exception:
                pass

        if db:

            try:
                db.close()
            except Exception:
                pass


# =========================================================
# MY CLAIMS
# =========================================================

@app.route("/my-claims")
def my_claims():

    if not login_required():

        return redirect(
            url_for("login")
        )

    db = None
    cursor = None
    claims = []

    try:

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True,
            buffered=True
        )

        cursor.execute(
            """
            SELECT
                c.id AS claim_id,
                c.claim_message,
                c.status AS claim_status,
                c.admin_note,
                c.created_at,

                l.id AS lost_item_id,
                l.item_name AS lost_item_name,
                l.category AS lost_category,
                l.description AS lost_description,
                l.lost_location,
                l.lost_date,
                l.color AS lost_color,

                f.id AS found_item_id,
                f.item_name AS found_item_name,
                f.category AS found_category,
                f.description AS found_description,
                f.found_location,
                f.found_date,
                f.color AS found_color

            FROM claims c

            INNER JOIN lost_items l
                ON c.lost_item_id = l.id

            INNER JOIN found_items f
                ON c.found_item_id = f.id

            WHERE c.claimant_id = %s

            ORDER BY c.created_at DESC
            """,
            (session["user_id"],)
        )

        claims = cursor.fetchall()

    except Exception as e:

        print(
            "MY CLAIMS ERROR:",
            repr(e)
        )

        flash(
            "Unable to load claims.",
            "error"
        )

    finally:

        if cursor:

            try:
                cursor.close()
            except Exception:
                pass

        if db:

            try:
                db.close()
            except Exception:
                pass

    return render_template(
        "my_claims.html",
        claims=claims
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin-dashboard")
def admin_dashboard():

    if not admin_required():

        if not login_required():

            return redirect(
                url_for("login")
            )

        flash(
            "Admin access required.",
            "error"
        )

        return redirect(
            url_for("dashboard")
        )

    db = None
    cursor = None

    total_users = 0
    total_lost = 0
    total_found = 0
    total_claims = 0
    pending_claims = 0
    approved_claims = 0
    rejected_claims = 0
    recent_claims = []

    try:

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True,
            buffered=True
        )

        cursor.execute(
            "SELECT COUNT(*) AS total FROM users"
        )

        result = cursor.fetchone()

        total_users = (
            result["total"]
            if result
            else 0
        )

        cursor.execute(
            "SELECT COUNT(*) AS total FROM lost_items"
        )

        result = cursor.fetchone()

        total_lost = (
            result["total"]
            if result
            else 0
        )

        cursor.execute(
            "SELECT COUNT(*) AS total FROM found_items"
        )

        result = cursor.fetchone()

        total_found = (
            result["total"]
            if result
            else 0
        )

        cursor.execute(
            "SELECT COUNT(*) AS total FROM claims"
        )

        result = cursor.fetchone()

        total_claims = (
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

        pending_claims = (
            result["total"]
            if result
            else 0
        )

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM claims
            WHERE status = 'Approved'
            """
        )

        result = cursor.fetchone()

        approved_claims = (
            result["total"]
            if result
            else 0
        )

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM claims
            WHERE status = 'Rejected'
            """
        )

        result = cursor.fetchone()

        rejected_claims = (
            result["total"]
            if result
            else 0
        )

        cursor.execute(
            """
            SELECT
                c.id AS claim_id,
                c.claim_message,
                c.status AS claim_status,
                c.admin_note,
                c.created_at,

                u.name AS claimant_name,
                u.email AS claimant_email,

                l.item_name AS lost_item_name,
                l.category AS lost_category,

                f.item_name AS found_item_name,
                f.category AS found_category

            FROM claims c

            INNER JOIN users u
                ON c.claimant_id = u.id

            INNER JOIN lost_items l
                ON c.lost_item_id = l.id

            INNER JOIN found_items f
                ON c.found_item_id = f.id

            ORDER BY c.created_at DESC

            LIMIT 20
            """
        )

        recent_claims = cursor.fetchall()

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

            try:
                cursor.close()
            except Exception:
                pass

        if db:

            try:
                db.close()
            except Exception:
                pass

    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        total_lost=total_lost,
        total_found=total_found,
        total_claims=total_claims,
        pending_claims=pending_claims,
        approved_claims=approved_claims,
        rejected_claims=rejected_claims,
        recent_claims=recent_claims
    )


# =========================================================
# ADMIN CLAIMS
# =========================================================

@app.route("/admin/claims")
def admin_claims():

    if not admin_required():

        if not login_required():

            return redirect(
                url_for("login")
            )

        flash(
            "Admin access required.",
            "error"
        )

        return redirect(
            url_for("dashboard")
        )

    db = None
    cursor = None
    claims = []

    try:

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True,
            buffered=True
        )

        cursor.execute(
            """
            SELECT
                c.id AS claim_id,
                c.claim_message,
                c.status AS claim_status,
                c.admin_note,
                c.created_at,

                u.id AS claimant_id,
                u.name AS claimant_name,
                u.email AS claimant_email,

                l.id AS lost_item_id,
                l.item_name AS lost_item_name,
                l.category AS lost_category,
                l.description AS lost_description,
                l.lost_location,
                l.lost_date,
                l.color AS lost_color,
                l.identification_details AS lost_identification,

                f.id AS found_item_id,
                f.item_name AS found_item_name,
                f.category AS found_category,
                f.description AS found_description,
                f.found_location,
                f.found_date,
                f.color AS found_color,
                f.identification_details AS found_identification

            FROM claims c

            INNER JOIN users u
                ON c.claimant_id = u.id

            INNER JOIN lost_items l
                ON c.lost_item_id = l.id

            INNER JOIN found_items f
                ON c.found_item_id = f.id

            ORDER BY c.created_at DESC
            """
        )

        claims = cursor.fetchall()

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

            try:
                cursor.close()
            except Exception:
                pass

        if db:

            try:
                db.close()
            except Exception:
                pass

    return render_template(
        "admin_claims.html",
        claims=claims
    )


# =========================================================
# ADMIN UPDATE CLAIM
# =========================================================

@app.route(
    "/admin/claim/<int:claim_id>/update",
    methods=["POST"]
)
def admin_update_claim(
    claim_id
):

    if not admin_required():

        if not login_required():

            return redirect(
                url_for("login")
            )

        flash(
            "Admin access required.",
            "error"
        )

        return redirect(
            url_for("dashboard")
        )

    action = request.form.get(
        "action",
        ""
    ).strip().lower()

    admin_note = request.form.get(
        "admin_note",
        ""
    ).strip()

    if action not in [
        "approve",
        "reject"
    ]:

        flash(
            "Invalid claim action.",
            "error"
        )

        return redirect(
            url_for("admin_claims")
        )

    if not admin_note:

        if action == "approve":

            admin_note = (
                "Claim approved by administrator."
            )

        else:

            admin_note = (
                "Claim rejected by administrator."
            )

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True,
            buffered=True
        )

        cursor.execute(
            """
            SELECT
                id,
                found_item_id,
                claimant_id,
                lost_item_id,
                status
            FROM claims
            WHERE id = %s
            LIMIT 1
            """,
            (claim_id,)
        )

        claim = cursor.fetchone()

        if not claim:

            flash(
                "Claim not found.",
                "error"
            )

            return redirect(
                url_for("admin_claims")
            )

        if claim["status"] != "Pending":

            flash(
                "This claim has already been processed.",
                "error"
            )

            return redirect(
                url_for("admin_claims")
            )

        found_item_id = claim[
            "found_item_id"
        ]

        lost_item_id = claim[
            "lost_item_id"
        ]

        if action == "approve":

            cursor.execute(
                """
                SELECT
                    id,
                    status
                FROM found_items
                WHERE id = %s
                LIMIT 1
                """,
                (found_item_id,)
            )

            found_item = cursor.fetchone()

            if not found_item:

                flash(
                    "Found item no longer exists.",
                    "error"
                )

                return redirect(
                    url_for("admin_claims")
                )

            if found_item["status"] != "Found":

                flash(
                    "This found item is no longer available.",
                    "error"
                )

                return redirect(
                    url_for("admin_claims")
                )

            cursor.execute(
                """
                UPDATE claims
                SET
                    status = 'Approved',
                    admin_note = %s
                WHERE id = %s
                """,
                (
                    admin_note,
                    claim_id
                )
            )

            cursor.execute(
                """
                UPDATE lost_items
                SET status = 'Claimed'
                WHERE id = %s
                """,
                (lost_item_id,)
            )

            cursor.execute(
                """
                UPDATE found_items
                SET status = 'Claimed'
                WHERE id = %s
                """,
                (found_item_id,)
            )

            cursor.execute(
                """
                UPDATE claims
                SET
                    status = 'Rejected',
                    admin_note =
                        'This item was approved for another claim.'
                WHERE found_item_id = %s
                  AND id != %s
                  AND status = 'Pending'
                """,
                (
                    found_item_id,
                    claim_id
                )
            )

            db.commit()

            flash(
                "Claim approved successfully.",
                "success"
            )

        else:

            cursor.execute(
                """
                UPDATE claims
                SET
                    status = 'Rejected',
                    admin_note = %s
                WHERE id = %s
                """,
                (
                    admin_note,
                    claim_id
                )
            )

            db.commit()

            flash(
                "Claim rejected successfully.",
                "success"
            )

        return redirect(
            url_for("admin_claims")
        )

    except Exception as e:

        print(
            "ADMIN CLAIM UPDATE ERROR:",
            repr(e)
        )

        if db:

            try:
                db.rollback()
            except Exception:
                pass

        flash(
            "Unable to update claim.",
            "error"
        )

        return redirect(
            url_for("admin_claims")
        )

    finally:

        if cursor:

            try:
                cursor.close()
            except Exception:
                pass

        if db:

            try:
                db.close()
            except Exception:
                pass


# =========================================================
# TRACK
# =========================================================

@app.route("/track")
def track():

    if not login_required():

        return redirect(
            url_for("login")
        )

    db = None
    cursor = None

    reports = []
    claims = []

    try:

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True,
            buffered=True
        )

        user_id = session["user_id"]

        cursor.execute(
            """
            SELECT
                id,
                item_name,
                category,
                lost_location AS location,
                lost_date AS item_date,
                status,
                'Lost' AS report_type
            FROM lost_items
            WHERE user_id = %s

            UNION ALL

            SELECT
                id,
                item_name,
                category,
                found_location AS location,
                found_date AS item_date,
                status,
                'Found' AS report_type
            FROM found_items
            WHERE user_id = %s

            ORDER BY item_date DESC
            """,
            (
                user_id,
                user_id
            )
        )

        reports = cursor.fetchall()

        cursor.execute(
            """
            SELECT
                c.id AS claim_id,
                c.claim_message,
                c.status AS claim_status,
                c.admin_note,
                c.created_at,

                l.item_name AS lost_item_name,
                l.category AS lost_category,

                f.item_name AS found_item_name,
                f.category AS found_category,
                f.found_location

            FROM claims c

            INNER JOIN lost_items l
                ON c.lost_item_id = l.id

            INNER JOIN found_items f
                ON c.found_item_id = f.id

            WHERE c.claimant_id = %s

            ORDER BY c.created_at DESC
            """,
            (user_id,)
        )

        claims = cursor.fetchall()

    except Exception as e:

        print(
            "TRACK DATABASE ERROR:",
            repr(e)
        )

        flash(
            "Unable to load tracking information.",
            "error"
        )

        return redirect(
            url_for("dashboard")
        )

    finally:

        if cursor:

            try:
                cursor.close()
            except Exception:
                pass

        if db:

            try:
                db.close()
            except Exception:
                pass

    return render_template(
        "track.html",
        reports=reports,
        claims=claims
    )


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health")
def health():

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor()

        cursor.execute(
            "SELECT 1"
        )

        result = cursor.fetchone()

        return {
            "status": "ok",
            "application":
                "Smart Lost & Found Management System",
            "database": "connected",
            "test": result[0] if result else 1
        }, 200

    except Exception as e:

        print(
            "HEALTH CHECK ERROR:",
            repr(e)
        )

        return {
            "status": "error",
            "application":
                "Smart Lost & Found Management System",
            "database": "unavailable",
            "error": str(e)
        }, 503

    finally:

        if cursor:

            try:
                cursor.close()
            except Exception:
                pass

        if db:

            try:
                db.close()
            except Exception:
                pass


# =========================================================
# HOW IT WORKS
# =========================================================

@app.route("/how-it-works")
def how_it_works():

    return render_template(
        "how_it_works.html"
    )


# =========================================================
# HELP & SUPPORT
# =========================================================

@app.route("/help")
def help_page():

    return render_template(
        "help.html"
    )


# =========================================================
# PRIVACY POLICY
# =========================================================

@app.route("/privacy")
def privacy():

    return render_template(
        "privacy.html"
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("home")
    )


# =========================================================
# ERROR HANDLERS
# =========================================================

@app.errorhandler(404)
def page_not_found(error):

    print(
        "404 ERROR:",
        request.path
    )

    return render_template(
        "404.html"
    ), 404


@app.errorhandler(413)
def request_too_large(error):

    flash(
        "The uploaded/request data is too large. Maximum size is 5 MB.",
        "error"
    )

    return redirect(
        url_for("home")
    )


@app.errorhandler(500)
def internal_server_error(error):

    print(
        "500 ERROR:",
        repr(error)
    )

    return render_template(
        "500.html"
    ), 500


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        use_reloader=False
    )
