import os
import sqlite3
from datetime import date
from functools import wraps

from flask import Flask, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "elvariq-attendance-secret-key")
starter_employees = []
login_username = "admin"
login_password = os.environ.get("ADMIN_PASSWORD", "ElvaRiq123#")
database_path = os.environ.get("DATABASE_PATH", "attendance.db")


def get_connection():
    return sqlite3.connect(database_path)


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if session.get("role") != "admin":
            return redirect(url_for("login"))

        return view(*args, **kwargs)

    return wrapped_view


def employee_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if session.get("role") != "employee":
            return redirect(url_for("login"))

        return view(*args, **kwargs)

    return wrapped_view


def create_tables():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            phone TEXT,
            email TEXT,
            department TEXT,
            username TEXT,
            password TEXT
        )
        """
    )
    cursor.execute("PRAGMA table_info(employees)")
    employee_columns = [column[1] for column in cursor.fetchall()]

    if "username" not in employee_columns:
        cursor.execute("ALTER TABLE employees ADD COLUMN username TEXT")

    if "password" not in employee_columns:
        cursor.execute("ALTER TABLE employees ADD COLUMN password TEXT")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_name TEXT NOT NULL,
            status TEXT NOT NULL,
            attendance_date TEXT NOT NULL
        )
        """
    )

    for employee in starter_employees:
        cursor.execute(
            "INSERT OR IGNORE INTO employees (name) VALUES (?)",
            (employee,),
        )

    connection.commit()
    connection.close()


def add_employee(name, phone, email, department, username, password):
    username = username or None
    password = password or None

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT OR IGNORE INTO employees (name, phone, email, department, username, password)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (name, phone, email, department, username, password),
    )
    connection.commit()
    connection.close()


def get_employees():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT id, name, phone, email, department, username
        FROM employees
        ORDER BY name
        """
    )
    employees = cursor.fetchall()
    connection.close()
    return employees


def get_employee_names():
    return [employee[1] for employee in get_employees()]


def get_employee_count():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM employees")
    total = cursor.fetchone()[0]
    connection.close()
    return total


def get_employee(employee_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT id, name, phone, email, department, username, password
        FROM employees
        WHERE id = ?
        """,
        (employee_id,),
    )
    employee = cursor.fetchone()
    connection.close()
    return employee


def update_employee(employee_id, name, phone, email, department, username, password):
    username = username or None
    password = password or None

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        UPDATE employees
        SET name = ?, phone = ?, email = ?, department = ?, username = ?, password = ?
        WHERE id = ?
        """,
        (name, phone, email, department, username, password, employee_id),
    )
    connection.commit()
    connection.close()


def get_employee_by_login(username, password):
    if not username or not password:
        return None

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT id, name
        FROM employees
        WHERE username = ? AND password = ?
        """,
        (username, password),
    )
    employee = cursor.fetchone()
    connection.close()
    return employee


def reset_employee_login(name, email, username, password):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        UPDATE employees
        SET username = ?, password = ?
        WHERE LOWER(name) = LOWER(?) AND LOWER(email) = LOWER(?)
        """,
        (username, password, name, email),
    )
    updated_count = cursor.rowcount
    connection.commit()
    connection.close()
    return updated_count > 0


def delete_employee(employee_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "DELETE FROM employees WHERE id = ?",
        (employee_id,),
    )
    connection.commit()
    connection.close()


def save_attendance(attendance_date, attendance):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM attendance WHERE attendance_date = ?",
        (attendance_date,),
    )

    for employee, status in attendance.items():
        cursor.execute(
            """
            INSERT INTO attendance (employee_name, status, attendance_date)
            VALUES (?, ?, ?)
            """,
            (employee, status, attendance_date),
        )

    connection.commit()
    connection.close()


def save_employee_attendance(attendance_date, employee_name, status):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        DELETE FROM attendance
        WHERE attendance_date = ? AND employee_name = ?
        """,
        (attendance_date, employee_name),
    )
    cursor.execute(
        """
        INSERT INTO attendance (employee_name, status, attendance_date)
        VALUES (?, ?, ?)
        """,
        (employee_name, status, attendance_date),
    )
    connection.commit()
    connection.close()


def get_employee_attendance(attendance_date, employee_name):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT status
        FROM attendance
        WHERE attendance_date = ? AND employee_name = ?
        """,
        (attendance_date, employee_name),
    )
    record = cursor.fetchone()
    connection.close()
    return record[0] if record else ""


def get_attendance(attendance_date):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT employee_name, status
        FROM attendance
        WHERE attendance_date = ?
        ORDER BY employee_name
        """,
        (attendance_date,),
    )
    records = cursor.fetchall()
    connection.close()
    return records


def get_attendance_summary(attendance_date):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT status, COUNT(*)
        FROM attendance
        WHERE attendance_date = ?
        GROUP BY status
        """,
        (attendance_date,),
    )
    summary = dict(cursor.fetchall())
    connection.close()

    return {
        "Present": summary.get("Present", 0),
        "Absent": summary.get("Absent", 0),
    }


def get_all_attendance():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT attendance_date, employee_name, status
        FROM attendance
        ORDER BY attendance_date DESC, employee_name
        """
    )
    records = cursor.fetchall()
    connection.close()
    return records


@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username == login_username and password == login_password:
            session["role"] = "admin"
            return redirect(url_for("dashboard"))

        employee = get_employee_by_login(username, password)
        if employee:
            session["role"] = "employee"
            session["employee_id"] = employee[0]
            session["employee_name"] = employee[1]
            return redirect(url_for("my_attendance"))

        error = "Invalid username or password"

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/forgot-login", methods=["GET", "POST"])
def forgot_login():
    error = ""
    message = ""

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not name or not email or not username or not password:
            error = "Please fill all fields"
        elif reset_employee_login(name, email, username, password):
            message = "Login details updated. You can login now."
        else:
            error = "Employee name and email did not match"

    return render_template("forgot_login.html", error=error, message=message)


@app.route("/")
@admin_required
def dashboard():
    today = date.today().isoformat()
    employee_count = get_employee_count()
    saved_attendance = get_attendance(today)
    summary = get_attendance_summary(today)
    marked_count = summary["Present"] + summary["Absent"]
    not_marked_count = employee_count - marked_count

    return render_template(
        "dashboard.html",
        today=today,
        employee_count=employee_count,
        present_count=summary["Present"],
        absent_count=summary["Absent"],
        marked_count=marked_count,
        not_marked_count=not_marked_count,
        saved_attendance=saved_attendance,
    )


@app.route("/attendance", methods=["GET", "POST"])
@admin_required
def attendance():
    today = date.today().isoformat()
    employees = get_employee_names()
    attendance = {}

    if request.method == "POST":
        for employee in employees:
            attendance[employee] = request.form.get(employee)

        save_attendance(today, attendance)

    saved_attendance = get_attendance(today)

    return render_template(
        "index.html",
        employees=employees,
        attendance=attendance,
        saved_attendance=saved_attendance,
        today=today,
    )


@app.route("/employees", methods=["GET", "POST"])
@admin_required
def employees():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        department = request.form.get("department", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if name:
            add_employee(name, phone, email, department, username, password)

        return redirect(url_for("employees"))

    saved_employees = get_employees()
    return render_template("employees.html", employees=saved_employees)


@app.route("/employees/<int:employee_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_employee(employee_id):
    employee = get_employee(employee_id)

    if not employee:
        return redirect(url_for("employees"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        department = request.form.get("department", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if name:
            update_employee(employee_id, name, phone, email, department, username, password)

        return redirect(url_for("employees"))

    return render_template("edit_employee.html", employee=employee)


@app.route("/employees/<int:employee_id>/delete", methods=["POST"])
@admin_required
def remove_employee(employee_id):
    delete_employee(employee_id)
    return redirect(url_for("employees"))


@app.route("/records")
@admin_required
def records():
    saved_records = get_all_attendance()
    return render_template("records.html", saved_records=saved_records)


@app.route("/my-attendance", methods=["GET", "POST"])
@employee_required
def my_attendance():
    today = date.today().isoformat()
    employee_name = session["employee_name"]

    if request.method == "POST":
        status = request.form.get("status", "").strip()

        if status:
            save_employee_attendance(today, employee_name, status)

    saved_status = get_employee_attendance(today, employee_name)

    return render_template(
        "my_attendance.html",
        employee_name=employee_name,
        today=today,
        saved_status=saved_status,
    )


if __name__ == "__main__":
    create_tables()
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)


create_tables()
