import os

from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from database import get_db, init_db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-this-secret")

# Auto-initialize database on startup
init_db()

# --- AUTH ROUTES ---

@app.route("/")
def index():
    if "user_id" in session:
        if session["role"] == "department":
            return redirect(url_for("dept_dashboard"))
        elif session["role"] == "startup":
            return redirect(url_for("startup_dashboard"))
        elif session["role"] == "admin":
            return redirect(url_for("admin_dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            return redirect(url_for("index"))
        else:
            flash("Invalid email or password.")
            return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
                (name, email, generate_password_hash(password), role)
            )
            conn.commit()
            flash("Registration successful. Please log in.")
            return redirect(url_for("login"))
        except:
            flash("Email already exists.")
        finally:
            conn.close()

    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# --- DEPARTMENT ROUTES ---

@app.route("/department/dashboard")
def dept_dashboard():
    if session.get("role") != "department":
        return redirect(url_for("login"))

    conn = get_db()
    challenges = conn.execute(
        "SELECT * FROM challenges WHERE dept_id = ? ORDER BY id DESC",
        (session["user_id"],)
    ).fetchall()

    # Metrics
    total_challenges = len(challenges)
    total_apps = conn.execute(
        """SELECT COUNT(*) FROM applications a 
           JOIN challenges c ON a.challenge_id = c.id 
           WHERE c.dept_id = ?""", (session["user_id"],)
    ).fetchone()[0]

    # Applications breakdown by status
    status_counts = conn.execute(
        """SELECT a.status, COUNT(*) as count FROM applications a
           JOIN challenges c ON a.challenge_id = c.id
           WHERE c.dept_id = ? GROUP BY a.status""", (session["user_id"],)
    ).fetchall()

    conn.close()
    return render_template(
        "dept_dashboard.html",
        challenges=challenges,
        total_challenges=total_challenges,
        total_apps=total_apps,
        status_counts=status_counts
    )

@app.route("/department/challenge/new", methods=["GET", "POST"])
def new_challenge():
    if session.get("role") != "department":
        return redirect(url_for("login"))

    if request.method == "POST":
        conn = get_db()
        conn.execute(
            """INSERT INTO challenges (dept_id, title, description, expected_outcome, budget, timeline, theme)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (session["user_id"], request.form["title"], request.form["description"],
             request.form["expected_outcome"], request.form["budget"],
             request.form["timeline"], request.form["theme"])
        )
        conn.commit()
        conn.close()
        return redirect(url_for("dept_dashboard"))

    return render_template("new_challenge.html")

@app.route("/department/challenge/<int:challenge_id>/applications")
def challenge_applications(challenge_id):
    if session.get("role") != "department":
        return redirect(url_for("login"))

    conn = get_db()
    challenge = conn.execute("SELECT * FROM challenges WHERE id = ?", (challenge_id,)).fetchone()
    applications = conn.execute(
        "SELECT * FROM applications WHERE challenge_id = ? ORDER BY id DESC",
        (challenge_id,)
    ).fetchall()
    conn.close()

    return render_template("challenge_applications.html", challenge=challenge, applications=applications)

@app.route("/application/status/<int:app_id>", methods=["POST"])
def update_status(app_id):
    if session.get("role") not in ["department", "admin"]:
        return redirect(url_for("login"))

    new_status = request.form["status"]
    challenge_id = request.form["challenge_id"]

    conn = get_db()
    conn.execute("UPDATE applications SET status = ? WHERE id = ?", (new_status, app_id))
    conn.commit()
    conn.close()

    return redirect(url_for("challenge_applications", challenge_id=challenge_id))


# --- STARTUP ROUTES ---

@app.route("/startup/dashboard")
def startup_dashboard():
    if session.get("role") != "startup":
        return redirect(url_for("login"))

    search = request.args.get("search", "")
    theme_filter = request.args.get("theme", "")

    query = "SELECT * FROM challenges WHERE status = 'Active'"
    params = []

    if search:
        query += " AND (title LIKE ? OR description LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    if theme_filter:
        query += " AND theme = ?"
        params.append(theme_filter)

    query += " ORDER BY id DESC"

    conn = get_db()
    challenges = conn.execute(query, params).fetchall()

    # Fetch applications submitted by this startup
    my_applications = conn.execute(
        """SELECT a.*, c.title as challenge_title FROM applications a
           JOIN challenges c ON a.challenge_id = c.id
           WHERE a.startup_id = ? ORDER BY a.id DESC""",
        (session["user_id"],)
    ).fetchall()

    conn.close()
    return render_template("startup_dashboard.html", challenges=challenges, my_applications=my_applications)

@app.route("/challenge/<int:challenge_id>", methods=["GET", "POST"])
def challenge_detail(challenge_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    challenge = conn.execute("SELECT * FROM challenges WHERE id = ?", (challenge_id,)).fetchone()

    # Check if this startup already applied
    already_applied = None
    if session.get("role") == "startup":
        already_applied = conn.execute(
            "SELECT * FROM applications WHERE challenge_id = ? AND startup_id = ?",
            (challenge_id, session["user_id"])
        ).fetchone()

    if request.method == "POST" and session.get("role") == "startup":
        if not already_applied:
            conn.execute(
                """INSERT INTO applications (challenge_id, startup_id, startup_name, solution_summary, team_size, contact_info)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (challenge_id, session["user_id"], session["name"],
                 request.form["solution_summary"], request.form["team_size"],
                 request.form["contact_info"])
            )
            conn.commit()
            conn.close()
            return redirect(url_for("startup_dashboard"))

    conn.close()
    return render_template("challenge_detail.html", challenge=challenge, already_applied=already_applied)


# --- ADMIN & TEMPLATES ROUTES ---

@app.route("/admin/dashboard")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db()
    total_challenges = conn.execute("SELECT COUNT(*) FROM challenges").fetchone()[0]
    total_startups = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'startup'").fetchone()[0]
    total_applications = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
    status_counts = conn.execute("SELECT status, COUNT(*) as count FROM applications GROUP BY status").fetchall()
    all_challenges = conn.execute("SELECT * FROM challenges ORDER BY id DESC").fetchall()
    conn.close()

    return render_template(
        "admin_dashboard.html",
        total_challenges=total_challenges,
        total_startups=total_startups,
        total_applications=total_applications,
        status_counts=status_counts,
        all_challenges=all_challenges
    )

@app.route("/admin/toggle_challenge/<int:challenge_id>")
def toggle_challenge(challenge_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db()
    ch = conn.execute("SELECT status FROM challenges WHERE id = ?", (challenge_id,)).fetchone()
    new_status = "Closed" if ch["status"] == "Active" else "Active"
    conn.execute("UPDATE challenges SET status = ? WHERE id = ?", (new_status, challenge_id))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_dashboard"))

@app.route("/templates")
def templates_library():
    return render_template("templates_library.html")

if __name__ == "__main__":
    app.run(
        host=os.environ.get("APP_HOST", "127.0.0.1"),
        port=int(os.environ.get("APP_PORT", "5001")),
        debug=os.environ.get("FLASK_DEBUG", "0") == "1",
    )