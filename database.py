import os
import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_NAME = Path(os.environ.get("DATABASE_PATH", BASE_DIR / "procure.db")).expanduser()


def get_db():
    DB_NAME.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_NAME, timeout=10)
    conn.row_factory = sqlite3.Row  # Access columns by name: row['title']
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # 1. Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL, -- 'department', 'startup', 'admin'
            email_verified INTEGER NOT NULL DEFAULT 1
        )
    """)
    user_columns = {row["name"] for row in cursor.execute("PRAGMA table_info(users)").fetchall()}
    if "email_verified" not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 1")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_verification_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_hash TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    # 2. Challenges Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dept_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            expected_outcome TEXT NOT NULL,
            budget TEXT,
            timeline TEXT,
            theme TEXT NOT NULL,
            status TEXT DEFAULT 'Active', -- 'Active', 'Closed'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dept_id) REFERENCES users (id)
        )
    """)

    # 3. Applications Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            challenge_id INTEGER NOT NULL,
            startup_id INTEGER NOT NULL,
            startup_name TEXT NOT NULL,
            solution_summary TEXT NOT NULL,
            team_size INTEGER,
            contact_info TEXT,
            status TEXT DEFAULT 'Screening', -- 'Screening', 'Shortlisted', 'Pilot', 'Completed', 'Scaled', 'Rejected'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (challenge_id) REFERENCES challenges (id),
            FOREIGN KEY (startup_id) REFERENCES users (id)
        )
    """)

    cursor.executescript("""
        CREATE INDEX IF NOT EXISTS idx_challenges_department ON challenges (dept_id, status);
        CREATE INDEX IF NOT EXISTS idx_applications_challenge ON applications (challenge_id, status);
        CREATE INDEX IF NOT EXISTS idx_applications_startup ON applications (startup_id, created_at);
    """)

    # Seed Default Users if empty
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        sample_users = [
            ("MSInS Agriculture Dept", "dept@gov.in", generate_password_hash("dept123", method="pbkdf2:sha256"), "department", 1),
            ("AgriTech Solutions", "startup@test.com", generate_password_hash("startup123", method="pbkdf2:sha256"), "startup", 1),
            ("State Admin", "admin@gov.in", generate_password_hash("admin123", method="pbkdf2:sha256"), "admin", 1)
        ]
        cursor.executemany(
            "INSERT INTO users (name, email, password_hash, role, email_verified) VALUES (?, ?, ?, ?, ?)",
            sample_users
        )

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully with default users.")