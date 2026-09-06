from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_from_directory
)

import os
import re
from uuid import uuid4
from difflib import SequenceMatcher
from datetime import date

from mysql.connector import Error

from database import get_db_connection

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from werkzeug.utils import secure_filename


# =========================================================
# FLASK APPLICATION
# =========================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "smart_lost_found_secret_key_2026"
)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Maximum request size = 5 MB
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024


# =========================================================
# UPLOAD CONFIGURATION
# =========================================================

UPLOAD_FOLDER = os.path.join(
    app.root_path,
    "uploads"
)

ALLOWED_IMAGE_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "gif",
    "webp"
}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)


# =========================================================
# IMAGE HELPERS
# =========================================================

def allowed_image(filename):

    if not filename:
        return False

    if "." not in filename:
        return False

    extension = filename.rsplit(
        ".",
        1
    )[1].lower()

    return extension in ALLOWED_IMAGE_EXTENSIONS


def save_uploaded_image(uploaded_file):

    if not uploaded_file:
        return None

    if not uploaded_file.filename:
        return None

    original_filename = secure_filename(
        uploaded_file.filename
    )

    if not original_filename:

        raise ValueError(
            "Please select a valid image file."
        )

    if not allowed_image(
        original_filename
    ):

        raise ValueError(
            "Only JPG, JPEG, PNG, GIF and WEBP images are allowed."
        )

    extension = original_filename.rsplit(
        ".",
        1
    )[1].lower()

    unique_filename = (
        uuid4().hex
        + "."
        + extension
    )

    save_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        unique_filename
    )

    uploaded_file.save(
        save_path
    )

    return unique_filename


def delete_uploaded_image(filename):

    if not filename:
        return

    safe_filename = secure_filename(
        filename
    )

    if not safe_filename:
        return

    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        safe_filename
    )

    try:

        if os.path.isfile(file_path):

            os.remove(
                file_path
            )

    except OSError as error:

        print(
            "Unable to delete image:",
            error
        )


# =========================================================
# SIMILARITY / SMART MATCHING
# =========================================================

def similarity(value1, value2):

    value1 = str(
        value1 or ""
    ).strip().lower()

    value2 = str(
        value2 or ""
    ).strip().lower()

    if not value1 or not value2:

        return 0

    return SequenceMatcher(
        None,
        value1,
        value2
    ).ratio()


def calculate_match(lost_item, found_item):

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
        category_score * 0.25
        + name_score * 0.25
        + description_score * 0.20
        + location_score * 0.20
        + color_score * 0.10
    )

    return round(
        total_score * 100,
        2
    )


# =========================================================
# LOGIN REQUIRED
# =========================================================

def login_required():

    if "user_id" not in session:

        flash(
            "Please login to continue.",
            "warning"
        )

        return False

    return True


# =========================================================
# ADMIN REQUIRED
# =========================================================

def admin_required():

    if "user_id" not in session:

        flash(
            "Please login to continue.",
            "warning"
        )

        return False

    if session.get("user_role") != "admin":

        flash(
            "Admin access is required.",
            "danger"
        )

        return False

    return True


# =========================================================
# HOME
# =========================================================

@app.route("/")
def index():

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
# HOW IT WORKS
# =========================================================

@app.route("/how-it-works")
def how_it_works():

    return render_template(
        "how_it_works.html"
    )


# =========================================================
# HELP
# =========================================================

@app.route("/help")
def help():

    return render_template(
        "help.html"
    )


# =========================================================
# PRIVACY
# =========================================================

@app.route("/privacy")
def privacy():

    return render_template(
        "privacy.html"
    )


# =========================================================
# REGISTER
# =========================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "GET":

        return render_template(
            "register.html"
        )

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

    confirm_password = request.form.get(
        "confirm_password",
        ""
    )

    # -----------------------------------------------------
    # NAME VALIDATION
    # -----------------------------------------------------

    if not name:

        flash(
            "Name is required.",
            "danger"
        )

        return render_template(
            "register.html"
        )

    if len(name) > 100:

        flash(
            "Name is too long.",
            "danger"
        )

        return render_template(
            "register.html"
        )

    # -----------------------------------------------------
    # EMAIL VALIDATION
    # -----------------------------------------------------

    email_pattern = (
        r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    )

    if not re.match(
        email_pattern,
        email
    ):

        flash(
            "Please enter a valid email address.",
            "danger"
        )

        return render_template(
            "register.html"
        )

    # -----------------------------------------------------
    # PASSWORD VALIDATION
    # -----------------------------------------------------

    if len(password) < 6:

        flash(
            "Password must contain at least 6 characters.",
            "danger"
        )

        return render_template(
            "register.html"
        )

    if password != confirm_password:

        flash(
            "Passwords do not match.",
            "danger"
        )

        return render_template(
            "register.html"
        )

    # -----------------------------------------------------
    # DATABASE CONNECTION
    # -----------------------------------------------------

    connection = get_db_connection()

    if connection is None:

        flash(
            "Database error. Please try again.",
            "danger"
        )

        return render_template(
            "register.html"
        )

    cursor = None

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE email = %s
            """,
            (email,)
        )

        existing_user = cursor.fetchone()

        if existing_user:

            flash(
                "An account with this email already exists.",
                "danger"
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

    except Error as error:

        connection.rollback()

        print(
            "Registration error:",
            error
        )

        flash(
            "Unable to create account. Please try again.",
            "danger"
        )

        return render_template(
            "register.html"
        )

    finally:

        if cursor:

            cursor.close()

        connection.close()


# =========================================================
# LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "GET":

        return render_template(
            "login.html"
        )

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
            "danger"
        )

        return render_template(
            "login.html"
        )

    connection = get_db_connection()

    if connection is None:

        flash(
            "Database error. Please try again.",
            "danger"
        )

        return render_template(
            "login.html"
        )

    cursor = None

    try:

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
            """,
            (email,)
        )

        user = cursor.fetchone()

        if not user:

            flash(
                "Invalid email or password.",
                "danger"
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
                "danger"
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

    except Error as error:

        print(
            "Login error:",
            error
        )

        flash(
            "Unable to login. Please try again.",
            "danger"
        )

        return render_template(
            "login.html"
        )

    finally:

        if cursor:

            cursor.close()

        connection.close()


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if not login_required():

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    if connection is None:

        flash(
            "Database error. Please try again.",
            "danger"
        )

        return render_template(
            "dashboard.html",
            total_reports=0,
            found_reports=0,
            possible_matches=0,
            successful_recoveries=0
        )

    cursor = None

    try:

        cursor = connection.cursor()

        user_id = session["user_id"]

        # -------------------------------------------------
        # LOST REPORT COUNT
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM lost_items
            WHERE user_id = %s
            """,
            (user_id,)
        )

        lost_count = cursor.fetchone()[0]

        # -------------------------------------------------
        # FOUND REPORT COUNT
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM found_items
            WHERE user_id = %s
            """,
            (user_id,)
        )

        found_count = cursor.fetchone()[0]

        total_reports = (
            lost_count
            + found_count
        )

        # -------------------------------------------------
        # POSSIBLE MATCHES
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                l.category AS lost_category,
                l.item_name AS lost_item_name,
                l.description AS lost_description,
                l.lost_location,
                l.color AS lost_color,

                f.category AS found_category,
                f.item_name AS found_item_name,
                f.description AS found_description,
                f.found_location,
                f.color AS found_color

            FROM lost_items l

            INNER JOIN found_items f
                ON l.category = f.category

            WHERE l.user_id = %s
            AND l.status = 'Lost'
            AND f.status = 'Found'
            """,
            (user_id,)
        )

        possible_matches = 0

        possible_match_rows = cursor.fetchall()

        for row in possible_match_rows:

            match_score = calculate_match(
                {
                    "category": row[0],
                    "item_name": row[1],
                    "description": row[2],
                    "lost_location": row[3],
                    "color": row[4]
                },
                {
                    "category": row[5],
                    "item_name": row[6],
                    "description": row[7],
                    "found_location": row[8],
                    "color": row[9]
                }
            )

            if match_score >= 35:

                possible_matches += 1

        # -------------------------------------------------
        # SUCCESSFUL RECOVERIES
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM claims c

            INNER JOIN lost_items l
                ON c.lost_item_id = l.id

            WHERE c.claimant_id = %s
            AND c.status = 'Approved'
            """,
            (user_id,)
        )

        successful_recoveries = cursor.fetchone()[0]

        return render_template(
            "dashboard.html",
            total_reports=total_reports,
            found_reports=found_count,
            possible_matches=possible_matches,
            successful_recoveries=successful_recoveries
        )

    except Error as error:

        print(
            "Dashboard error:",
            error
        )

        return render_template(
            "dashboard.html",
            total_reports=0,
            found_reports=0,
            possible_matches=0,
            successful_recoveries=0
        )

    finally:

        if cursor:

            cursor.close()

        connection.close()


# =========================================================
# REPORT LOST ITEM
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

    if request.method == "GET":

        return render_template(
            "report_lost.html"
        )

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

    # -----------------------------------------------------
    # REQUIRED FIELD VALIDATION
    # -----------------------------------------------------

    if not item_name:

        flash(
            "Item name is required.",
            "danger"
        )

        return render_template(
            "report_lost.html"
        )

    if not category:

        flash(
            "Please select a category.",
            "danger"
        )

        return render_template(
            "report_lost.html"
        )

    if not description:

        flash(
            "Description is required.",
            "danger"
        )

        return render_template(
            "report_lost.html"
        )

    if not lost_location:

        flash(
            "Lost location is required.",
            "danger"
        )

        return render_template(
            "report_lost.html"
        )

    if not lost_date:

        flash(
            "Lost date is required.",
            "danger"
        )

        return render_template(
            "report_lost.html"
        )

    # -----------------------------------------------------
    # LENGTH VALIDATION
    # -----------------------------------------------------

    if len(item_name) > 150:

        flash(
            "Item name is too long.",
            "danger"
        )

        return render_template(
            "report_lost.html"
        )

    if len(description) > 1000:

        flash(
            "Description is too long.",
            "danger"
        )

        return render_template(
            "report_lost.html"
        )

    if len(lost_location) > 200:

        flash(
            "Lost location is too long.",
            "danger"
        )

        return render_template(
            "report_lost.html"
        )

    if len(color) > 50:

        flash(
            "Color is too long.",
            "danger"
        )

        return render_template(
            "report_lost.html"
        )

    if len(identification_details) > 1000:

        flash(
            "Identification details are too long.",
            "danger"
        )

        return render_template(
            "report_lost.html"
        )

    # -----------------------------------------------------
    # DATE VALIDATION
    # -----------------------------------------------------

    try:

        parsed_lost_date = date.fromisoformat(
            lost_date
        )

        if parsed_lost_date > date.today():

            flash(
                "Lost date cannot be in the future.",
                "danger"
            )

            return render_template(
                "report_lost.html"
            )

    except ValueError:

        flash(
            "Please enter a valid lost date.",
            "danger"
        )

        return render_template(
            "report_lost.html"
        )

    # -----------------------------------------------------
    # IMAGE UPLOAD
    # -----------------------------------------------------

    uploaded_image = request.files.get(
        "image"
    )

    saved_image = None

    try:

        saved_image = save_uploaded_image(
            uploaded_image
        )

    except ValueError as error:

        flash(
            str(error),
            "danger"
        )

        return render_template(
            "report_lost.html"
        )

    # -----------------------------------------------------
    # DATABASE
    # -----------------------------------------------------

    connection = get_db_connection()

    if connection is None:

        if saved_image:

            delete_uploaded_image(
                saved_image
            )

        flash(
            "Database error. Please try again.",
            "danger"
        )

        return render_template(
            "report_lost.html"
        )

    cursor = None

    try:

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
                saved_image,
                "Lost"
            )
        )

        connection.commit()

        flash(
            "Lost item report submitted successfully.",
            "success"
        )

        return redirect(
            url_for("my_reports")
        )

    except Error as error:

        connection.rollback()

        if saved_image:

            delete_uploaded_image(
                saved_image
            )

        print(
            "Report lost error:",
            error
        )

        flash(
            "Unable to submit the report. Please try again.",
            "danger"
        )

        return render_template(
            "report_lost.html"
        )

    finally:

        if cursor:

            cursor.close()

        connection.close()


# =========================================================
# REPORT FOUND ITEM
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

    if request.method == "GET":

        return render_template(
            "report_found.html"
        )

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

    # -----------------------------------------------------
    # REQUIRED FIELD VALIDATION
    # -----------------------------------------------------

    if not item_name:

        flash(
            "Item name is required.",
            "danger"
        )

        return render_template(
            "report_found.html"
        )

    if not category:

        flash(
            "Please select a category.",
            "danger"
        )

        return render_template(
            "report_found.html"
        )

    if not description:

        flash(
            "Description is required.",
            "danger"
        )

        return render_template(
            "report_found.html"
        )

    if not found_location:

        flash(
            "Found location is required.",
            "danger"
        )

        return render_template(
            "report_found.html"
        )

    if not found_date:

        flash(
            "Found date is required.",
            "danger"
        )

        return render_template(
            "report_found.html"
        )

    # -----------------------------------------------------
    # LENGTH VALIDATION
    # -----------------------------------------------------

    if len(item_name) > 150:

        flash(
            "Item name is too long.",
            "danger"
        )

        return render_template(
            "report_found.html"
        )

    if len(description) > 1000:

        flash(
            "Description is too long.",
            "danger"
        )

        return render_template(
            "report_found.html"
        )

    if len(found_location) > 200:

        flash(
            "Found location is too long.",
            "danger"
        )

        return render_template(
            "report_found.html"
        )

    if len(color) > 50:

        flash(
            "Color is too long.",
            "danger"
        )

        return render_template(
            "report_found.html"
        )

    if len(identification_details) > 1000:

        flash(
            "Identification details are too long.",
            "danger"
        )

        return render_template(
            "report_found.html"
        )

    # -----------------------------------------------------
    # DATE VALIDATION
    # -----------------------------------------------------

    try:

        parsed_found_date = date.fromisoformat(
            found_date
        )

        if parsed_found_date > date.today():

            flash(
                "Found date cannot be in the future.",
                "danger"
            )

            return render_template(
                "report_found.html"
            )

    except ValueError:

        flash(
            "Please enter a valid found date.",
            "danger"
        )

        return render_template(
            "report_found.html"
        )

    # -----------------------------------------------------
    # IMAGE UPLOAD
    # -----------------------------------------------------

    uploaded_image = request.files.get(
        "image"
    )

    saved_image = None

    try:

        saved_image = save_uploaded_image(
            uploaded_image
        )

    except ValueError as error:

        flash(
            str(error),
            "danger"
        )

        return render_template(
            "report_found.html"
        )

    # -----------------------------------------------------
    # DATABASE
    # -----------------------------------------------------

    connection = get_db_connection()

    if connection is None:

        if saved_image:

            delete_uploaded_image(
                saved_image
            )

        flash(
            "Database error. Please try again.",
            "danger"
        )

        return render_template(
            "report_found.html"
        )

    cursor = None

    try:

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
                saved_image,
                "Found"
            )
        )

        connection.commit()

        flash(
            "Found item report submitted successfully.",
            "success"
        )

        return redirect(
            url_for("my_reports")
        )

    except Error as error:

        connection.rollback()

        if saved_image:

            delete_uploaded_image(
                saved_image
            )

        print(
            "Report found error:",
            error
        )

        flash(
            "Unable to submit the report. Please try again.",
            "danger"
        )

        return render_template(
            "report_found.html"
        )

    finally:

        if cursor:

            cursor.close()

        connection.close()


# =========================================================
# SERVE UPLOADED IMAGES
# =========================================================

@app.route(
    "/uploads/<path:filename>"
)
def uploaded_file(filename):

    safe_filename = secure_filename(
        filename
    )

    if not safe_filename:

        return redirect(
            url_for("index")
        )

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        safe_filename
    )


# =========================================================
# SEARCH
# =========================================================

@app.route("/search")
def search():

    if not login_required():

        return redirect(
            url_for("login")
        )

    query = request.args.get(
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
    ).strip().lower()

    location = request.args.get(
        "location",
        ""
    ).strip()

    connection = get_db_connection()

    if connection is None:

        flash(
            "Database error. Please try again.",
            "danger"
        )

        return render_template(
            "search.html",
            results=[],
            query=query,
            category=category,
            item_type=item_type,
            location=location
        )

    cursor = None

    try:

        cursor = connection.cursor(
            dictionary=True
        )

        results = []

        # -------------------------------------------------
        # SEARCH LOST ITEMS
        # -------------------------------------------------

        if item_type in [
            "",
            "lost"
        ]:

            lost_sql = """
                SELECT
                    l.*,
                    u.name AS reporter_name,
                    'Lost' AS report_type
                FROM lost_items l

                INNER JOIN users u
                    ON l.user_id = u.id

                WHERE 1 = 1
            """

            lost_params = []

            if query:

                lost_sql += """
                    AND (
                        l.item_name LIKE %s
                        OR l.description LIKE %s
                        OR l.lost_location LIKE %s
                        OR l.color LIKE %s
                        OR l.identification_details LIKE %s
                    )
                """

                search_value = (
                    "%"
                    + query
                    + "%"
                )

                lost_params.extend([
                    search_value,
                    search_value,
                    search_value,
                    search_value,
                    search_value
                ])

            if category:

                lost_sql += """
                    AND l.category = %s
                """

                lost_params.append(
                    category
                )

            if location:

                lost_sql += """
                    AND l.lost_location LIKE %s
                """

                lost_params.append(
                    "%"
                    + location
                    + "%"
                )

            lost_sql += """
                ORDER BY l.created_at DESC
            """

            cursor.execute(
                lost_sql,
                tuple(lost_params)
            )

            results.extend(
                cursor.fetchall()
            )

        # -------------------------------------------------
        # SEARCH FOUND ITEMS
        # -------------------------------------------------

        if item_type in [
            "",
            "found"
        ]:

            found_sql = """
                SELECT
                    f.*,
                    u.name AS reporter_name,
                    'Found' AS report_type
                FROM found_items f

                INNER JOIN users u
                    ON f.user_id = u.id

                WHERE 1 = 1
            """

            found_params = []

            if query:

                found_sql += """
                    AND (
                        f.item_name LIKE %s
                        OR f.description LIKE %s
                        OR f.found_location LIKE %s
                        OR f.color LIKE %s
                        OR f.identification_details LIKE %s
                    )
                """

                search_value = (
                    "%"
                    + query
                    + "%"
                )

                found_params.extend([
                    search_value,
                    search_value,
                    search_value,
                    search_value,
                    search_value
                ])

            if category:

                found_sql += """
                    AND f.category = %s
                """

                found_params.append(
                    category
                )

            if location:

                found_sql += """
                    AND f.found_location LIKE %s
                """

                found_params.append(
                    "%"
                    + location
                    + "%"
                )

            found_sql += """
                ORDER BY f.created_at DESC
            """

            cursor.execute(
                found_sql,
                tuple(found_params)
            )

            results.extend(
                cursor.fetchall()
            )

        results.sort(
            key=lambda item: item.get(
                "created_at"
            ),
            reverse=True
        )

        return render_template(
            "search.html",
            results=results,
            query=query,
            category=category,
            item_type=item_type,
            location=location
        )

    except Error as error:

        print(
            "Search error:",
            error
        )

        flash(
            "Unable to perform search.",
            "danger"
        )

        return render_template(
            "search.html",
            results=[],
            query=query,
            category=category,
            item_type=item_type,
            location=location
        )

    finally:

        if cursor:

            cursor.close()

        connection.close()


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

    item_type = item_type.lower()

    if item_type not in [
        "lost",
        "found"
    ]:

        flash(
            "Invalid item type.",
            "danger"
        )

        return redirect(
            url_for("search")
        )

    connection = get_db_connection()

    if connection is None:

        flash(
            "Database error. Please try again.",
            "danger"
        )

        return redirect(
            url_for("search")
        )

    cursor = None

    try:

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

                INNER JOIN users u
                    ON l.user_id = u.id

                WHERE l.id = %s
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

                INNER JOIN users u
                    ON f.user_id = u.id

                WHERE f.id = %s
                """,
                (item_id,)
            )

        item = cursor.fetchone()

        if not item:

            flash(
                "Item not found.",
                "danger"
            )

            return redirect(
                url_for("search")
            )

        item["item_type"] = item_type

        return render_template(
            "item_details.html",
            item=item
        )

    except Error as error:

        print(
            "Item details error:",
            error
        )

        flash(
            "Unable to load item details.",
            "danger"
        )

        return redirect(
            url_for("search")
        )

    finally:

        if cursor:

            cursor.close()

        connection.close()


# =========================================================
# SMART MATCHES
# =========================================================

@app.route("/matches")
def matches():

    if not login_required():

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    if connection is None:

        flash(
            "Database error. Please try again.",
            "danger"
        )

        return render_template(
            "matches.html",
            matches=[]
        )

    cursor = None

    try:

        cursor = connection.cursor(
            dictionary=True
        )

        user_id = session["user_id"]

        # -------------------------------------------------
        # USER LOST ITEMS
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT *
            FROM lost_items

            WHERE user_id = %s
            AND status = 'Lost'

            ORDER BY created_at DESC
            """,
            (user_id,)
        )

        lost_items = cursor.fetchall()

        # -------------------------------------------------
        # ALL ACTIVE FOUND ITEMS
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                f.*,
                u.name AS reporter_name

            FROM found_items f

            INNER JOIN users u
                ON f.user_id = u.id

            WHERE f.status = 'Found'

            ORDER BY f.created_at DESC
            """
        )

        found_items = cursor.fetchall()

        # -------------------------------------------------
        # CALCULATE MATCHES
        # -------------------------------------------------

        all_matches = []

        for lost_item in lost_items:

            for found_item in found_items:

                match_score = calculate_match(
                    lost_item,
                    found_item
                )

                if match_score >= 35:

                    all_matches.append({
                        "lost_item": lost_item,
                        "found_item": found_item,
                        "score": match_score
                    })

        all_matches.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        return render_template(
            "matches.html",
            matches=all_matches
        )

    except Error as error:

        print(
            "Matching error:",
            error
        )

        flash(
            "Unable to calculate matches.",
            "danger"
        )

        return render_template(
            "matches.html",
            matches=[]
        )

    finally:

        if cursor:

            cursor.close()

        connection.close()


# =========================================================
# MY REPORTS
# =========================================================

@app.route("/my-reports")
def my_reports():

    if not login_required():

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    if connection is None:

        flash(
            "Database error. Please try again.",
            "danger"
        )

        return render_template(
            "my_reports.html",
            reports=[]
        )

    cursor = None

    try:

        cursor = connection.cursor(
            dictionary=True
        )

        user_id = session["user_id"]

        # -------------------------------------------------
        # LOST REPORTS
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                item_name,
                description,
                category,
                lost_location AS location,
                lost_date AS item_date,
                color,
                status,
                image,
                created_at,
                'Lost' AS report_type

            FROM lost_items

            WHERE user_id = %s
            """,
            (user_id,)
        )

        lost_reports = cursor.fetchall()

        # -------------------------------------------------
        # FOUND REPORTS
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                item_name,
                description,
                category,
                found_location AS location,
                found_date AS item_date,
                color,
                status,
                image,
                created_at,
                'Found' AS report_type

            FROM found_items

            WHERE user_id = %s
            """,
            (user_id,)
        )

        found_reports = cursor.fetchall()

        reports = (
            lost_reports
            + found_reports
        )

        reports.sort(
            key=lambda item: item.get(
                "created_at"
            ),
            reverse=True
        )

        return render_template(
            "my_reports.html",
            reports=reports
        )

    except Error as error:

        print(
            "My reports error:",
            error
        )

        flash(
            "Unable to load your reports.",
            "danger"
        )

        return render_template(
            "my_reports.html",
            reports=[]
        )

    finally:

        if cursor:

            cursor.close()

        connection.close()


# =========================================================
# CLAIM ITEM
# =========================================================

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

    connection = get_db_connection()

    if connection is None:

        flash(
            "Database error. Please try again.",
            "danger"
        )

        return redirect(
            url_for("matches")
        )

    cursor = None

    try:

        cursor = connection.cursor(
            dictionary=True
        )

        # -------------------------------------------------
        # GET FOUND ITEM
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT *
            FROM found_items
            WHERE id = %s
            """,
            (found_item_id,)
        )

        found_item = cursor.fetchone()

        # -------------------------------------------------
        # GET USER'S LOST ITEM
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT *
            FROM lost_items

            WHERE id = %s
            AND user_id = %s
            """,
            (
                lost_item_id,
                session["user_id"]
            )
        )

        lost_item = cursor.fetchone()

        if not found_item or not lost_item:

            flash(
                "Invalid claim request.",
                "danger"
            )

            return redirect(
                url_for("matches")
            )

        # -------------------------------------------------
        # USER CANNOT CLAIM OWN FOUND REPORT
        # -------------------------------------------------

        if found_item["user_id"] == session["user_id"]:

            flash(
                "You cannot claim your own found item report.",
                "warning"
            )

            return redirect(
                url_for("matches")
            )

        # -------------------------------------------------
        # FOUND ITEM MUST BE AVAILABLE
        # -------------------------------------------------

        if found_item["status"] != "Found":

            flash(
                "This found item is no longer available for claiming.",
                "warning"
            )

            return redirect(
                url_for("matches")
            )

        # -------------------------------------------------
        # LOST ITEM MUST STILL BE LOST
        # -------------------------------------------------

        if lost_item["status"] != "Lost":

            flash(
                "This lost report is already resolved.",
                "warning"
            )

            return redirect(
                url_for("matches")
            )

        # -------------------------------------------------
        # GET CLAIM PAGE
        # -------------------------------------------------

        if request.method == "GET":

            return render_template(
                "claim.html",
                found_item=found_item,
                lost_item=lost_item
            )

        # -------------------------------------------------
        # CLAIM MESSAGE
        # -------------------------------------------------

        claim_message = request.form.get(
            "claim_message",
            ""
        ).strip()

        if not claim_message:

            flash(
                "Claim message is required.",
                "danger"
            )

            return render_template(
                "claim.html",
                found_item=found_item,
                lost_item=lost_item
            )

        if len(claim_message) < 10:

            flash(
                "Claim explanation must contain at least 10 characters.",
                "danger"
            )

            return render_template(
                "claim.html",
                found_item=found_item,
                lost_item=lost_item
            )

        if len(claim_message) > 2000:

            flash(
                "Claim explanation must not exceed 2000 characters.",
                "danger"
            )

            return render_template(
                "claim.html",
                found_item=found_item,
                lost_item=lost_item
            )

        # -------------------------------------------------
        # CHECK EXISTING CLAIM
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                status

            FROM claims

            WHERE found_item_id = %s
            AND claimant_id = %s
            AND lost_item_id = %s
            AND status IN ('Pending', 'Approved')
            """,
            (
                found_item_id,
                session["user_id"],
                lost_item_id
            )
        )

        existing_claim = cursor.fetchone()

        if existing_claim:

            if existing_claim["status"] == "Approved":

                flash(
                    "This claim has already been approved.",
                    "warning"
                )

            else:

                flash(
                    "You have already submitted a claim for this item.",
                    "warning"
                )

            return redirect(
                url_for("my_claims")
            )

        # -------------------------------------------------
        # CHECK APPROVED CLAIM FOR FOUND ITEM
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT id
            FROM claims

            WHERE found_item_id = %s
            AND status = 'Approved'
            """,
            (found_item_id,)
        )

        approved_claim = cursor.fetchone()

        if approved_claim:

            flash(
                "This found item has already been claimed successfully.",
                "warning"
            )

            return redirect(
                url_for("matches")
            )

        # -------------------------------------------------
        # INSERT CLAIM
        # -------------------------------------------------

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

    except Error as error:

        connection.rollback()

        print(
            "Claim error:",
            error
        )

        flash(
            "Unable to submit claim.",
            "danger"
        )

        return redirect(
            url_for("matches")
        )

    finally:

        if cursor:

            cursor.close()

        connection.close()


# =========================================================
# MY CLAIMS
# =========================================================

@app.route("/my-claims")
def my_claims():

    if not login_required():

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    if connection is None:

        flash(
            "Database error. Please try again.",
            "danger"
        )

        return render_template(
            "my_claims.html",
            claims=[]
        )

    cursor = None

    try:

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT

                c.id AS claim_id,
                c.found_item_id,
                c.claimant_id,
                c.lost_item_id,
                c.claim_message,
                c.status AS claim_status,
                c.admin_note,
                c.created_at,

                f.item_name AS found_item_name,
                f.category AS found_category,
                f.found_location,
                f.found_date,
                f.color AS found_color,
                f.image AS found_image,

                l.item_name AS lost_item_name,
                l.category AS lost_category,
                l.lost_location,
                l.lost_date,
                l.color AS lost_color,
                l.image AS lost_image

            FROM claims c

            INNER JOIN found_items f
                ON c.found_item_id = f.id

            INNER JOIN lost_items l
                ON c.lost_item_id = l.id

            WHERE c.claimant_id = %s

            ORDER BY c.created_at DESC
            """,
            (session["user_id"],)
        )

        claims = cursor.fetchall()

        return render_template(
            "my_claims.html",
            claims=claims
        )

    except Error as error:

        print(
            "My claims error:",
            error
        )

        flash(
            "Unable to load your claims.",
            "danger"
        )

        return render_template(
            "my_claims.html",
            claims=[]
        )

    finally:

        if cursor:

            cursor.close()

        connection.close()


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin-dashboard")
def admin_dashboard():

    if not admin_required():

        return redirect(
            url_for("dashboard")
        )

    connection = get_db_connection()

    if connection is None:

        flash(
            "Database error. Please try again.",
            "danger"
        )

        return render_template(
            "admin_dashboard.html",
            total_users=0,
            total_lost=0,
            total_found=0,
            total_claims=0,
            pending_claims=0,
            approved_claims=0,
            rejected_claims=0
        )

    cursor = None

    try:

        cursor = connection.cursor()

        # -------------------------------------------------
        # TOTAL USERS
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM users
            """
        )

        total_users = cursor.fetchone()[0]

        # -------------------------------------------------
        # TOTAL LOST
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM lost_items
            """
        )

        total_lost = cursor.fetchone()[0]

        # -------------------------------------------------
        # TOTAL FOUND
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM found_items
            """
        )

        total_found = cursor.fetchone()[0]

        # -------------------------------------------------
        # TOTAL CLAIMS
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM claims
            """
        )

        total_claims = cursor.fetchone()[0]

        # -------------------------------------------------
        # PENDING CLAIMS
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM claims
            WHERE status = 'Pending'
            """
        )

        pending_claims = cursor.fetchone()[0]

        # -------------------------------------------------
        # APPROVED CLAIMS
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM claims
            WHERE status = 'Approved'
            """
        )

        approved_claims = cursor.fetchone()[0]

        # -------------------------------------------------
        # REJECTED CLAIMS
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM claims
            WHERE status = 'Rejected'
            """
        )

        rejected_claims = cursor.fetchone()[0]

        return render_template(
            "admin_dashboard.html",
            total_users=total_users,
            total_lost=total_lost,
            total_found=total_found,
            total_claims=total_claims,
            pending_claims=pending_claims,
            approved_claims=approved_claims,
            rejected_claims=rejected_claims
        )

    except Error as error:

        print(
            "Admin dashboard error:",
            error
        )

        return render_template(
            "admin_dashboard.html",
            total_users=0,
            total_lost=0,
            total_found=0,
            total_claims=0,
            pending_claims=0,
            approved_claims=0,
            rejected_claims=0
        )

    finally:

        if cursor:

            cursor.close()

        connection.close()


# =========================================================
# ADMIN CLAIM MANAGEMENT
# =========================================================

@app.route("/admin/claims")
def admin_claims():

    if not admin_required():

        return redirect(
            url_for("dashboard")
        )

    connection = get_db_connection()

    if connection is None:

        flash(
            "Database error. Please try again.",
            "danger"
        )

        return render_template(
            "admin_claims.html",
            claims=[]
        )

    cursor = None

    try:

        cursor = connection.cursor(
            dictionary=True
        )

        # -------------------------------------------------
        # IMPORTANT:
        #
        # c.status AS claim_status
        #
        # This matches:
        #
        # claim.claim_status
        #
        # used by admin_claims.html
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT

                c.id AS claim_id,
                c.found_item_id,
                c.claimant_id,
                c.lost_item_id,
                c.claim_message,
                c.status AS claim_status,
                c.admin_note,
                c.created_at,

                u.name AS claimant_name,
                u.email AS claimant_email,

                l.item_name AS lost_item_name,
                l.category AS lost_category,
                l.lost_location AS lost_location,
                l.lost_date AS lost_date,
                l.color AS lost_color,
                l.description AS lost_description,
                l.identification_details AS lost_identification,

                f.item_name AS found_item_name,
                f.category AS found_category,
                f.found_location AS found_location,
                f.found_date AS found_date,
                f.color AS found_color,
                f.description AS found_description,
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

        return render_template(
            "admin_claims.html",
            claims=claims
        )

    except Error as error:

        print(
            "Admin claims error:",
            error
        )

        flash(
            "Unable to load claims.",
            "danger"
        )

        return render_template(
            "admin_claims.html",
            claims=[]
        )

    finally:

        if cursor:

            cursor.close()

        connection.close()


# =========================================================
# ADMIN UPDATE CLAIM
# =========================================================

@app.route(
    "/admin/claim/<int:claim_id>/update",
    methods=["POST"]
)
def update_claim(claim_id):

    if not admin_required():

        return redirect(
            url_for("dashboard")
        )

    # =====================================================
    # IMPORTANT FIX
    #
    # admin_claims.html sends:
    #
    # name="action"
    #
    # Therefore backend MUST read "action".
    # =====================================================

    action = request.form.get(
        "action",
        ""
    ).strip()

    admin_note = request.form.get(
        "admin_note",
        ""
    ).strip()

    allowed_actions = {
        "Pending",
        "Approved",
        "Rejected"
    }

    if action not in allowed_actions:

        flash(
            "Invalid claim action.",
            "danger"
        )

        return redirect(
            url_for("admin_claims")
        )

    if len(admin_note) > 2000:

        flash(
            "Admin note is too long.",
            "danger"
        )

        return redirect(
            url_for("admin_claims")
        )

    connection = get_db_connection()

    if connection is None:

        flash(
            "Database error. Please try again.",
            "danger"
        )

        return redirect(
            url_for("admin_claims")
        )

    cursor = None

    try:

        cursor = connection.cursor(
            dictionary=True
        )

        # -------------------------------------------------
        # GET CLAIM
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT

                id,
                found_item_id,
                lost_item_id,
                claimant_id,
                status

            FROM claims

            WHERE id = %s
            """,
            (claim_id,)
        )

        claim_record = cursor.fetchone()

        if not claim_record:

            flash(
                "Claim not found.",
                "danger"
            )

            return redirect(
                url_for("admin_claims")
            )

        # =================================================
        # APPROVE CLAIM
        # =================================================

        if action == "Approved":

            # -------------------------------------------------
            # DO NOT APPROVE IF CLAIM IS ALREADY APPROVED
            # BY SOME OTHER CLAIMANT
            # -------------------------------------------------

            cursor.execute(
                """
                SELECT id

                FROM claims

                WHERE found_item_id = %s
                AND status = 'Approved'
                AND id != %s
                """,
                (
                    claim_record["found_item_id"],
                    claim_id
                )
            )

            another_approved_claim = cursor.fetchone()

            if another_approved_claim:

                flash(
                    "Another claim for this found item is already approved.",
                    "warning"
                )

                return redirect(
                    url_for("admin_claims")
                )

            # -------------------------------------------------
            # APPROVE CURRENT CLAIM
            # -------------------------------------------------

            cursor.execute(
                """
                UPDATE claims

                SET
                    status = %s,
                    admin_note = %s

                WHERE id = %s
                """,
                (
                    "Approved",
                    admin_note,
                    claim_id
                )
            )

            # -------------------------------------------------
            # UPDATE USER LOST ITEM
            #
            # Lost -> Returned
            # -------------------------------------------------

            cursor.execute(
                """
                UPDATE lost_items

                SET status = 'Returned'

                WHERE id = %s
                """,
                (
                    claim_record["lost_item_id"],
                )
            )

            # -------------------------------------------------
            # UPDATE FOUND ITEM
            #
            # Found -> Claimed
            # -------------------------------------------------

            cursor.execute(
                """
                UPDATE found_items

                SET status = 'Claimed'

                WHERE id = %s
                """,
                (
                    claim_record["found_item_id"],
                )
            )

            # -------------------------------------------------
            # REJECT OTHER PENDING CLAIMS
            # -------------------------------------------------

            cursor.execute(
                """
                UPDATE claims

                SET
                    status = 'Rejected',
                    admin_note = 'Another claim for this item was approved.'

                WHERE found_item_id = %s
                AND id != %s
                AND status = 'Pending'
                """,
                (
                    claim_record["found_item_id"],
                    claim_id
                )
            )

        # =================================================
        # REJECT CLAIM
        # =================================================

        elif action == "Rejected":

            cursor.execute(
                """
                UPDATE claims

                SET
                    status = %s,
                    admin_note = %s

                WHERE id = %s
                """,
                (
                    "Rejected",
                    admin_note,
                    claim_id
                )
            )

        # =================================================
        # KEEP CLAIM PENDING
        # =================================================

        else:

            cursor.execute(
                """
                UPDATE claims

                SET
                    status = %s,
                    admin_note = %s

                WHERE id = %s
                """,
                (
                    "Pending",
                    admin_note,
                    claim_id
                )
            )

        # -------------------------------------------------
        # COMMIT
        # -------------------------------------------------

        connection.commit()

        if action == "Approved":

            flash(
                "Claim approved successfully.",
                "success"
            )

        elif action == "Rejected":

            flash(
                "Claim rejected successfully.",
                "success"
            )

        else:

            flash(
                "Claim kept as pending.",
                "success"
            )

        return redirect(
            url_for("admin_claims")
        )

    except Error as error:

        connection.rollback()

        print(
            "Update claim error:",
            error
        )

        flash(
            "Unable to update claim.",
            "danger"
        )

        return redirect(
            url_for("admin_claims")
        )

    finally:

        if cursor:

            cursor.close()

        connection.close()


# =========================================================
# TRACK STATUS
# =========================================================

@app.route("/track")
def track():

    if not login_required():

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    if connection is None:

        flash(
            "Database error. Please try again.",
            "danger"
        )

        return render_template(
            "track.html",
            reports=[],
            claims=[]
        )

    cursor = None

    try:

        cursor = connection.cursor(
            dictionary=True
        )

        user_id = session["user_id"]

        # -------------------------------------------------
        # LOST REPORTS
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT

                id,
                item_name,
                category,
                lost_location AS location,
                lost_date AS item_date,
                status,
                created_at,
                'Lost' AS report_type

            FROM lost_items

            WHERE user_id = %s
            """,
            (user_id,)
        )

        lost_reports = cursor.fetchall()

        # -------------------------------------------------
        # FOUND REPORTS
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT

                id,
                item_name,
                category,
                found_location AS location,
                found_date AS item_date,
                status,
                created_at,
                'Found' AS report_type

            FROM found_items

            WHERE user_id = %s
            """,
            (user_id,)
        )

        found_reports = cursor.fetchall()

        reports = (
            lost_reports
            + found_reports
        )

        reports.sort(
            key=lambda item: item.get(
                "created_at"
            ),
            reverse=True
        )

        # -------------------------------------------------
        # USER CLAIMS
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT

                c.id AS claim_id,
                c.found_item_id,
                c.claimant_id,
                c.lost_item_id,
                c.claim_message,
                c.status AS claim_status,
                c.admin_note,
                c.created_at,

                f.item_name AS found_item_name,
                l.item_name AS lost_item_name

            FROM claims c

            INNER JOIN found_items f
                ON c.found_item_id = f.id

            INNER JOIN lost_items l
                ON c.lost_item_id = l.id

            WHERE c.claimant_id = %s

            ORDER BY c.created_at DESC
            """,
            (user_id,)
        )

        claims = cursor.fetchall()

        return render_template(
            "track.html",
            reports=reports,
            claims=claims
        )

    except Error as error:

        print(
            "Track error:",
            error
        )

        flash(
            "Unable to load tracking information.",
            "danger"
        )

        return render_template(
            "track.html",
            reports=[],
            claims=[]
        )

    finally:

        if cursor:

            cursor.close()

        connection.close()


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health")
def health():

    connection = None

    try:

        connection = get_db_connection()

        if connection is None:

            return {
                "status": "unavailable",
                "database": "unavailable"
            }, 503

        if connection.is_connected():

            return {
                "status": "ok",
                "database": "connected"
            }, 200

        return {
            "status": "unavailable",
            "database": "unavailable"
        }, 503

    except Error as error:

        print(
            "Health check database error:",
            error
        )

        return {
            "status": "unavailable",
            "database": "unavailable"
        }, 503

    except Exception as error:

        print(
            "Health check error:",
            error
        )

        return {
            "status": "unavailable",
            "database": "unavailable"
        }, 503

    finally:

        if connection:

            try:

                connection.close()

            except Exception:

                pass


# =========================================================
# LOGOUT
# =========================================================

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


# =========================================================
# 404 ERROR
# =========================================================

@app.errorhandler(404)
def page_not_found(error):

    return render_template(
        "404.html"
    ), 404


# =========================================================
# 413 ERROR - FILE TOO LARGE
# =========================================================

@app.errorhandler(413)
def request_entity_too_large(error):

    flash(
        "Uploaded image is too large. Maximum size is 5 MB.",
        "danger"
    )

    referrer = request.referrer or ""

    if "/report-found" in referrer:

        return redirect(
            url_for("report_found")
        )

    return redirect(
        url_for("report_lost")
    )


# =========================================================
# 500 ERROR
# =========================================================

@app.errorhandler(500)
def internal_server_error(error):

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