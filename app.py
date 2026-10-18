import secrets
import io

import qrcode

import sqlite3
from pathlib import Path
from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    send_file,
    url_for,
    redirect,
    session,
    flash
)

from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
import os

from functools import wraps

app.secret_key = os.environ.get("HANDOFF_SECRET_KEY")

if not app.secret_key:
    raise RuntimeError(
        "Set HANDOFF_SECRET_KEY before starting HANDOFF"
    )

# Database file project ke main folder mein banegi
DB_PATH = Path(__file__).resolve().parent / "handoff.db"

def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to access HANDOFF.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped_view

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS responsibilities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                status TEXT DEFAULT 'Pending'
            )
        """)
        # Add new fields safely to an existing database
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(responsibilities)").fetchall()
        }

        if "assigned_to" not in columns:
            conn.execute(
                "ALTER TABLE responsibilities ADD COLUMN assigned_to TEXT DEFAULT ''"
            )

        if "qr_token" not in columns:
            conn.execute(
                "ALTER TABLE responsibilities ADD COLUMN qr_token TEXT"
            )

        # Give existing responsibilities a unique QR token
        rows = conn.execute(
            "SELECT id FROM responsibilities WHERE qr_token IS NULL OR qr_token = ''"
        ).fetchall()

        for row in rows:
            token = secrets.token_urlsafe(24)
            conn.execute(
                "UPDATE responsibilities SET qr_token = ? WHERE id = ?",
                (token, row["id"])
            )

        conn.execute("""
            CREATE TABLE IF NOT EXISTS trusted_contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS emergency_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER NOT NULL,
                situation_notes TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (
                    datetime('now', 'localtime')
                ),
                FOREIGN KEY (contact_id)
                    REFERENCES trusted_contacts(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS emergency_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                responsibility_id INTEGER NOT NULL,
                alert_status TEXT NOT NULL DEFAULT 'Pending',
                alert_message TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (
                    datetime('now', 'localtime')
                ),
                FOREIGN KEY (responsibility_id)
                    REFERENCES responsibilities(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notification_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id INTEGER NOT NULL,
                recipient_type TEXT NOT NULL,
                delivery_status TEXT NOT NULL DEFAULT 'DEMO_ONLY_NOT_SENT',
                message TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (
                    datetime('now', 'localtime')
                ),
                FOREIGN KEY (alert_id)
                    REFERENCES emergency_alerts(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (
                    datetime('now', 'localtime')
                )
            )
        """)


# Database aur tables startup par ready honge
init_db()


@app.route("/")
@login_required
def home():
    return render_template("index.html")
    

@app.route("/responsibility/<token>")
def responsibility_detail(token):
    with get_db() as conn:
        row = conn.execute("""
            SELECT  id,title, description, status, assigned_to
            FROM responsibilities
            WHERE qr_token = ?
        """, (token,)).fetchone()

    if row is None:
        return "Responsibility not found or QR is invalid.", 404

    return render_template(
        "responsibility_detail.html",
        task=dict(row)
    )


@app.route("/responsibility/<token>/qr.png")
def responsibility_qr(token):
    with get_db() as conn:
        row = conn.execute("""
            SELECT id FROM responsibilities
            WHERE qr_token = ?
        """, (token,)).fetchone()

    if row is None:
        return jsonify({"error": "Responsibility not found"}), 404

    link = url_for(
        "responsibility_detail",
        token=token,
        _external=True
    )

    qr_image = qrcode.make(link)
    buffer = io.BytesIO()
    qr_image.save(buffer, format="PNG")
    buffer.seek(0)

    return send_file(buffer, mimetype="image/png")


@app.route("/api/health")
def health():
    return jsonify({
        "status": "healthy",
        "project": "HANDOFF"
    })


# Responsibilities: database se read karo
@app.route("/api/responsibilities", methods=["GET"])
@login_required
def get_responsibilities():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM responsibilities ORDER BY id"
        ).fetchall()

    return jsonify([dict(row) for row in rows])


# Responsibility database mein add karo
@app.route("/api/responsibilities", methods=["POST"])
@login_required
def add_responsibility():
    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    assigned_to = data.get("assigned_to", "").strip()

    if not title:
        return jsonify({"error": "Title is required"}), 400

    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO responsibilities (title, description, assigned_to)
               VALUES (?, ?, ?)""",
            (title, description, assigned_to)
        )
        new_id = cursor.lastrowid

    return jsonify({
        "id": new_id,
        "title": title,
        "description": description,
        "assigned_to": assigned_to,
        "status": "Pending"
    }), 201

@app.route("/api/responsibilities/<int:responsibility_id>", methods=["DELETE"])
@login_required
def delete_responsibility(responsibility_id):
    with get_db() as conn:
        responsibility = conn.execute(
            "SELECT id FROM responsibilities WHERE id = ?",
            (responsibility_id,)
        ).fetchone()

        if responsibility is None:
            return jsonify({"error": "Responsibility not found"}), 404

        # Remove related demo alert logs first
        alert_rows = conn.execute(
            "SELECT id FROM emergency_alerts WHERE responsibility_id = ?",
            (responsibility_id,)
        ).fetchall()

        for alert in alert_rows:
            conn.execute(
                "DELETE FROM notification_logs WHERE alert_id = ?",
                (alert["id"],)
            )

        conn.execute(
            "DELETE FROM emergency_alerts WHERE responsibility_id = ?",
            (responsibility_id,)
        )

        conn.execute(
            "DELETE FROM responsibilities WHERE id = ?",
            (responsibility_id,)
        )

    return jsonify({
        "message": "Responsibility removed successfully",
        "id": responsibility_id
    }), 200

@app.route("/api/responsibilities/<int:responsibility_id>", methods=["PUT"])
@login_required
def update_responsibility(responsibility_id):
    data = request.get_json(silent=True) or {}

    title = data.get("title", "")
    description = data.get("description", "")
    status = data.get("status", "Pending")
    assigned_to = data.get("assigned_to", "")

    if not all(isinstance(value, str) for value in
               [title, description, status, assigned_to]):
        return jsonify({"error": "All fields must be text"}), 400

    title = title.strip()
    description = description.strip()
    status = status.strip()
    assigned_to = assigned_to.strip()

    if not title:
        return jsonify({"error": "Title is required"}), 400

    if len(title) > 200:
        return jsonify({"error": "Title must be 200 characters or fewer"}), 400

    if len(description) > 2000:
        return jsonify({"error": "Description must be 2000 characters or fewer"}), 400

    if len(assigned_to) > 100:
        return jsonify({"error": "Assigned person must be 100 characters or fewer"}), 400

    if status not in ["Pending", "In Progress", "Completed"]:
        return jsonify({"error": "Invalid status"}), 400

    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM responsibilities WHERE id = ?",
            (responsibility_id,)
        ).fetchone()

        if existing is None:
            return jsonify({"error": "Responsibility not found"}), 404

        conn.execute(
            """UPDATE responsibilities
               SET title = ?, description = ?, status = ?, assigned_to = ?
               WHERE id = ?""",
            (title, description, status, assigned_to, responsibility_id)
        )

    return jsonify({
        "message": "Responsibility updated successfully",
        "id": responsibility_id,
        "title": title,
        "description": description,
        "status": status,
        "assigned_to": assigned_to
    }), 200

# Trusted contacts: database se read karo
@app.route("/api/contacts", methods=["GET"])
@login_required
def get_contacts():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM trusted_contacts ORDER BY id"
        ).fetchall()

    return jsonify([dict(row) for row in rows])


# Trusted contact add karo
@app.route("/api/contacts", methods=["POST"])
@login_required
def add_contact():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()

    if not name or not phone:
        return jsonify({
            "error": "Name and phone are required"
        }), 400

    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO trusted_contacts (name, phone)
               VALUES (?, ?)""",
            (name, phone)
        )
        new_id = cursor.lastrowid

    return jsonify({
        "id": new_id,
        "name": name,
        "phone": phone
    }), 201

# Edit an existing trusted contact
@app.route("/api/contacts/<int:contact_id>", methods=["PUT"])
@login_required
def update_contact(contact_id):
    data = request.get_json(silent=True) or {}

    name = data.get("name", "")
    phone = data.get("phone", "")

    if not isinstance(name, str) or not isinstance(phone, str):
        return jsonify({"error": "Name and phone must be text"}), 400

    name = name.strip()
    phone = phone.strip()

    if not name or not phone:
        return jsonify({"error": "Name and phone are required"}), 400

    if len(name) > 100 or len(phone) > 30:
        return jsonify({"error": "Name or phone is too long"}), 400

    with get_db() as conn:
        cursor = conn.execute(
            """
            UPDATE trusted_contacts
            SET name = ?, phone = ?
            WHERE id = ?
            """,
            (name, phone, contact_id)
        )

        if cursor.rowcount == 0:
            return jsonify({"error": "Contact not found"}), 404

    return jsonify({
        "message": "Trusted contact updated successfully",
        "id": contact_id,
        "name": name,
        "phone": phone
    }), 200


# Remove an existing trusted contact
@app.route("/api/contacts/<int:contact_id>", methods=["DELETE"])
@login_required
def delete_contact(contact_id):
    with get_db() as conn:
        # Keep contacts that are referenced by emergency plans
        used = conn.execute(
            """
            SELECT 1 FROM emergency_plans
            WHERE contact_id = ?
            LIMIT 1
            """,
            (contact_id,)
        ).fetchone()

        if used:
            return jsonify({
                "error": "This contact is linked to an emergency plan. Update the plan first."
            }), 409

        cursor = conn.execute(
            "DELETE FROM trusted_contacts WHERE id = ?",
            (contact_id,)
        )

        if cursor.rowcount == 0:
            return jsonify({"error": "Contact not found"}), 404

    return jsonify({
        "message": "Trusted contact removed successfully",
        "id": contact_id
    }), 200

@app.route("/api/emergency-plans", methods=["POST"])
@login_required
def save_emergency_plan():
    data = request.get_json(silent=True) or {}

    contact_id = data.get("contact_id")
    notes = data.get("situation_notes", "")

    if not isinstance(notes, str):
        return jsonify({"error": "Situation notes must be text"}), 400

    notes = notes.strip()

    if len(notes) > 2000:
        return jsonify({"error": "Notes must be 2000 characters or fewer"}), 400

    try:
        contact_id = int(contact_id)
        if contact_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "Please select a valid trusted contact"}), 400

    with get_db() as conn:
        contact = conn.execute(
            "SELECT id, name FROM trusted_contacts WHERE id = ?",
            (contact_id,)
        ).fetchone()

        if contact is None:
            return jsonify({"error": "Selected trusted contact was not found"}), 404

        cursor = conn.execute(
            """INSERT INTO emergency_plans (contact_id, situation_notes)
               VALUES (?, ?)""",
            (contact_id, notes)
        )

        plan_id = cursor.lastrowid

        plan = conn.execute(
            """SELECT id, contact_id, situation_notes, created_at
               FROM emergency_plans WHERE id = ?""",
            (plan_id,)
        ).fetchone()

    return jsonify({
        "message": "Emergency plan saved successfully",
        "plan": dict(plan),
        "contact_name": contact["name"],
        "notification_sent": False
    }), 201

@app.route("/api/emergency-plans", methods=["GET"])
@login_required
def get_emergency_plans():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                emergency_plans.id,
                emergency_plans.contact_id,
                trusted_contacts.name AS contact_name,
                emergency_plans.situation_notes,
                emergency_plans.created_at
            FROM emergency_plans
            JOIN trusted_contacts
                ON trusted_contacts.id = emergency_plans.contact_id
            ORDER BY emergency_plans.id DESC
        """).fetchall()

    return jsonify([dict(row) for row in rows])  

@app.route("/api/emergency-plans/<int:plan_id>", methods=["PUT"])
@login_required
def update_emergency_plan(plan_id):
    data = request.get_json(silent=True) or {}

    contact_id = data.get("contact_id")
    notes = data.get("situation_notes", "")

    if not isinstance(notes, str):
        return jsonify({"error": "Situation notes must be text"}), 400

    notes = notes.strip()

    if len(notes) > 2000:
        return jsonify({"error": "Notes must be 2000 characters or fewer"}), 400

    try:
        contact_id = int(contact_id)
        if contact_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "Please select a valid trusted contact"}), 400

    with get_db() as conn:
        contact = conn.execute(
            "SELECT id, name FROM trusted_contacts WHERE id = ?",
            (contact_id,)
        ).fetchone()

        if contact is None:
            return jsonify({"error": "Selected trusted contact was not found"}), 404

        existing = conn.execute(
            "SELECT id FROM emergency_plans WHERE id = ?",
            (plan_id,)
        ).fetchone()

        if existing is None:
            return jsonify({"error": "Emergency plan not found"}), 404

        conn.execute(
            """UPDATE emergency_plans
               SET contact_id = ?, situation_notes = ?
               WHERE id = ?""",
            (contact_id, notes, plan_id)
        )

    return jsonify({
        "message": "Emergency plan updated successfully",
        "id": plan_id,
        "contact_id": contact_id,
        "contact_name": contact["name"],
        "situation_notes": notes
    }), 200


@app.route("/api/emergency-plans/<int:plan_id>", methods=["DELETE"])
@login_required
def delete_emergency_plan(plan_id):
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM emergency_plans WHERE id = ?",
            (plan_id,)
        )

        if cursor.rowcount == 0:
            return jsonify({"error": "Emergency plan not found"}), 404

    return jsonify({
        "message": "Emergency plan removed successfully",
        "id": plan_id
    }), 200

@app.route("/api/emergency-alerts", methods=["GET"])
@login_required
def get_emergency_alerts():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                emergency_alerts.id,
                emergency_alerts.responsibility_id,
                responsibilities.title AS responsibility_title,
                emergency_alerts.alert_status,
                emergency_alerts.alert_message,
                emergency_alerts.created_at
            FROM emergency_alerts
            JOIN responsibilities
                ON responsibilities.id =
                   emergency_alerts.responsibility_id
            ORDER BY emergency_alerts.id DESC
        """).fetchall()

    return jsonify([dict(row) for row in rows])

@app.route("/api/emergency-alerts", methods=["POST"])
def create_emergency_alert():
    data = request.get_json(silent=True) or {}
    responsibility_id = data.get("responsibility_id")

    try:
        responsibility_id = int(responsibility_id)
        if responsibility_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({
            "error": "Valid responsibility ID is required"
        }), 400

    with get_db() as conn:
        task = conn.execute("""
            SELECT id, title
            FROM responsibilities
            WHERE id = ?
        """, (responsibility_id,)).fetchone()

        if task is None:
            return jsonify({
                "error": "Responsibility not found"
            }), 404

        cursor = conn.execute("""
            INSERT INTO emergency_alerts
                (responsibility_id, alert_status, alert_message)
            VALUES (?, 'Pending', 'Demo request recorded; no notification sent')
        """, (responsibility_id,))

        alert_id = cursor.lastrowid
        demo_message = (
            "DEMO ONLY: No SMS, email, or authority notification was sent."
        )

        conn.executemany("""
            INSERT INTO notification_logs
                (alert_id, recipient_type, delivery_status, message)
            VALUES (?, ?, 'DEMO_ONLY_NOT_SENT', ?)
        """, [
            (alert_id, "Trusted Contact", demo_message),
            (alert_id, "Emergency Authority", demo_message)
        ])

        alert = conn.execute("""
            SELECT id, responsibility_id, alert_status,
                   alert_message, created_at
            FROM emergency_alerts
            WHERE id = ?
        """, (alert_id,)).fetchone()

    return jsonify({
        "message": "Demo emergency request recorded",
        "notification_sent": False,
        "alert": dict(alert)
    }), 201

@app.route("/api/notification-logs", methods=["GET"])
@login_required
def get_notification_logs():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                id,
                alert_id,
                recipient_type,
                delivery_status,
                message,
                created_at
            FROM notification_logs
            ORDER BY id DESC
        """).fetchall()

    return jsonify({
        "mode": "DEMO_ONLY",
        "real_notifications_enabled": False,
        "logs": [dict(row) for row in rows]
    })
    
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not name or not email or not password:
        flash("Please fill in all fields.", "error")
        return redirect(url_for("register"))

    if len(name) > 100 or len(email) > 254:
        flash("Name or email is too long.", "error")
        return redirect(url_for("register"))

    if len(password) < 8 or len(password) > 128:
        flash("Password must be 8 to 128 characters.", "error")
        return redirect(url_for("register"))

    password_hash = generate_password_hash(password)

    try:
        with get_db() as conn:
            conn.execute("""
                INSERT INTO users (name, email, password_hash)
                VALUES (?, ?, ?)
            """, (name, email, password_hash))
    except sqlite3.IntegrityError:
        flash("An account with this email already exists.", "error")
        return redirect(url_for("register"))

    flash("Registration successful. Please log in.", "success")
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("index"))
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        flash("Please enter your email and password.", "error")
        return redirect(url_for("login"))

    with get_db() as conn:
        user = conn.execute(
            """
            SELECT id, name, email, password_hash
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

    if user is None or not check_password_hash(
        user["password_hash"], password
    ):
        flash("Invalid email or password.", "error")
        return redirect(url_for("login"))

    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]

    flash("Login successful!", "success")
    return redirect("/")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)