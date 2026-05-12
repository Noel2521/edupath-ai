"""
EduPath AI v3 - Database Layer
New: institution_type (school/college/university), security audit log,
     brute-force protection, struggles visible to teacher, final-year flag.
"""

import sqlite3
import hashlib
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "edupath.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_tables():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS institutions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT    NOT NULL UNIQUE,
            city            TEXT,
            country         TEXT    DEFAULT 'United Kingdom',
            institution_type TEXT   DEFAULT 'college',
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            institution_id  INTEGER NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
            title           TEXT    NOT NULL,
            qualification   TEXT,
            level           TEXT,
            description     TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            institution_id  INTEGER REFERENCES institutions(id) ON DELETE SET NULL,
            full_name       TEXT    NOT NULL,
            email           TEXT    NOT NULL UNIQUE,
            password_hash   TEXT    NOT NULL,
            role            TEXT    DEFAULT 'teacher',
            last_login      TIMESTAMP,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            institution_id  INTEGER REFERENCES institutions(id) ON DELETE SET NULL,
            full_name       TEXT    NOT NULL,
            email           TEXT    NOT NULL UNIQUE,
            password_hash   TEXT    NOT NULL,
            year_group      TEXT,
            is_final_year   INTEGER DEFAULT 0,
            last_login      TIMESTAMP,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS enrolments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id  INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
            course_id   INTEGER NOT NULL REFERENCES courses(id)  ON DELETE CASCADE,
            enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_id, course_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS learning_plans (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id      INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
            course_id       INTEGER REFERENCES courses(id),
            subject         TEXT    NOT NULL,
            level           TEXT,
            goal            TEXT,
            struggles       TEXT,
            confidence      INTEGER,
            study_time      TEXT,
            duration_weeks  INTEGER DEFAULT 4,
            report          TEXT,
            risk_score      INTEGER,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS weekly_checkins (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id         INTEGER NOT NULL REFERENCES learning_plans(id) ON DELETE CASCADE,
            student_id      INTEGER NOT NULL REFERENCES students(id),
            week_number     INTEGER NOT NULL,
            completed_tasks TEXT,
            notes           TEXT,
            confidence      INTEGER,
            submitted_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id  INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
            plan_id     INTEGER REFERENCES learning_plans(id),
            week_number INTEGER,
            message     TEXT,
            is_read     INTEGER DEFAULT 0,
            due_date    DATE,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # UK GDPR / Cyber Essentials audit log
    c.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_type   TEXT,
            user_id     INTEGER,
            action      TEXT,
            ip_address  TEXT,
            user_agent  TEXT,
            detail      TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Brute-force protection
    c.execute("""
        CREATE TABLE IF NOT EXISTS failed_logins (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            email        TEXT,
            ip_address   TEXT,
            attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# ── Security helpers ──

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def log_audit(user_type, user_id, action, ip_address="", user_agent="", detail=""):
    conn = get_connection()
    conn.execute(
        "INSERT INTO audit_log (user_type, user_id, action, ip_address, user_agent, detail) VALUES (?,?,?,?,?,?)",
        (user_type, user_id, action, ip_address, user_agent, detail)
    )
    conn.commit()
    conn.close()


def count_failed_logins(email, ip_address, minutes=15):
    conn = get_connection()
    cutoff = datetime.now() - timedelta(minutes=minutes)
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM failed_logins WHERE (email=? OR ip_address=?) AND attempted_at > ?",
        (email, ip_address, cutoff)
    ).fetchone()
    conn.close()
    return row["cnt"] if row else 0


def record_failed_login(email, ip_address):
    conn = get_connection()
    conn.execute("INSERT INTO failed_logins (email, ip_address) VALUES (?,?)", (email, ip_address))
    conn.commit()
    conn.close()


# ── Auth ──

def register_student(institution_id, full_name, email, password, year_group="", is_final_year=False):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO students (institution_id, full_name, email, password_hash, year_group, is_final_year) VALUES (?,?,?,?,?,?)",
            (institution_id, full_name, email, hash_password(password), year_group, 1 if is_final_year else 0)
        )
        conn.commit()
        return True, "Account created successfully."
    except sqlite3.IntegrityError:
        return False, "Email already registered."
    finally:
        conn.close()


def login_student(email, password):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM students WHERE email=? AND password_hash=?",
        (email, hash_password(password))
    ).fetchone()
    if row:
        conn.execute("UPDATE students SET last_login=? WHERE id=?", (datetime.now(), row["id"]))
        conn.commit()
    conn.close()
    return dict(row) if row else None


def register_teacher(institution_id, full_name, email, password, role="teacher"):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO teachers (institution_id, full_name, email, password_hash, role) VALUES (?,?,?,?,?)",
            (institution_id, full_name, email, hash_password(password), role)
        )
        conn.commit()
        return True, "Account created."
    except sqlite3.IntegrityError:
        return False, "Email already registered."
    finally:
        conn.close()


def login_teacher(email, password):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM teachers WHERE email=? AND password_hash=?",
        (email, hash_password(password))
    ).fetchone()
    if row:
        conn.execute("UPDATE teachers SET last_login=? WHERE id=?", (datetime.now(), row["id"]))
        conn.commit()
    conn.close()
    return dict(row) if row else None


# ── Institutions ──

def get_all_institutions():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM institutions ORDER BY institution_type, name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_institution(name, city="", country="United Kingdom", institution_type="college"):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO institutions (name, city, country, institution_type) VALUES (?,?,?,?)",
            (name, city, country, institution_type)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_courses_by_institution(institution_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM courses WHERE institution_id=? ORDER BY qualification, title",
        (institution_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_course(institution_id, title, qualification, level, description=""):
    conn = get_connection()
    conn.execute(
        "INSERT INTO courses (institution_id, title, qualification, level, description) VALUES (?,?,?,?,?)",
        (institution_id, title, qualification, level, description)
    )
    conn.commit()
    conn.close()


def delete_course(course_id):
    conn = get_connection()
    conn.execute("DELETE FROM courses WHERE id=?", (course_id,))
    conn.commit()
    conn.close()


# ── Learning plans ──

def save_learning_plan(student_id, course_id, subject, level, goal, struggles,
                       confidence, study_time, duration_weeks, report, risk_score):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO learning_plans
        (student_id, course_id, subject, level, goal, struggles, confidence, study_time, duration_weeks, report, risk_score)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (student_id, course_id, subject, level, goal, struggles, confidence, study_time, duration_weeks, report, risk_score))
    plan_id = cursor.lastrowid
    conn.commit()
    conn.close()
    _schedule_reminders(student_id, plan_id, subject, duration_weeks)
    return plan_id


def get_plans_by_student(student_id):
    conn = get_connection()
    rows = conn.execute("""
        SELECT lp.*, c.title as course_title, c.qualification
        FROM learning_plans lp
        LEFT JOIN courses c ON lp.course_id = c.id
        WHERE lp.student_id = ?
        ORDER BY lp.created_at DESC
    """, (student_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_plan_by_id(plan_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM learning_plans WHERE id=?", (plan_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_plans_for_teacher(institution_id):
    conn = get_connection()
    rows = conn.execute("""
        SELECT s.full_name, s.year_group, s.is_final_year, s.email,
               lp.subject, lp.risk_score, lp.confidence, lp.struggles,
               lp.created_at, lp.id, lp.goal, lp.level
        FROM learning_plans lp
        JOIN students s ON s.id = lp.student_id
        WHERE s.institution_id = ?
        ORDER BY lp.risk_score DESC, lp.created_at DESC
    """, (institution_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_latest_plans_all():
    conn = get_connection()
    rows = conn.execute("""
        SELECT s.full_name, s.email, s.year_group, s.is_final_year,
               lp.subject, lp.risk_score, lp.struggles, lp.created_at, lp.id, lp.goal
        FROM learning_plans lp
        JOIN students s ON s.id = lp.student_id
        WHERE lp.id IN (SELECT MAX(id) FROM learning_plans GROUP BY student_id)
        ORDER BY lp.risk_score DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Check-ins ──

def save_checkin(plan_id, student_id, week_number, completed_tasks, notes, confidence):
    conn = get_connection()
    conn.execute("""
        INSERT INTO weekly_checkins (plan_id, student_id, week_number, completed_tasks, notes, confidence)
        VALUES (?,?,?,?,?,?)
    """, (plan_id, student_id, week_number, completed_tasks, notes, confidence))
    conn.commit()
    conn.close()


def get_checkins_by_plan(plan_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM weekly_checkins WHERE plan_id=? ORDER BY week_number",
        (plan_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Reminders ──

def _schedule_reminders(student_id, plan_id, subject, duration_weeks):
    conn = get_connection()
    today = datetime.now().date()
    msgs = [
        f"Week {{w}} — Time to review your {subject} plan and log progress!",
        f"Week {{w}} — Keep up the great work on {subject}. Submit your check-in.",
        f"Week {{w}} — Stay consistent! Your {subject} weekly check-in is due.",
        f"Week {{w}} — Almost there! Log your {subject} progress for this week.",
    ]
    for week in range(1, duration_weeks + 1):
        due = today + timedelta(weeks=week)
        msg = msgs[(week - 1) % len(msgs)].replace("{w}", str(week))
        conn.execute(
            "INSERT INTO reminders (student_id, plan_id, week_number, message, due_date) VALUES (?,?,?,?,?)",
            (student_id, plan_id, week, msg, due)
        )
    conn.commit()
    conn.close()


def get_reminders_for_student(student_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM reminders WHERE student_id=? ORDER BY due_date ASC",
        (student_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_reminder_read(reminder_id):
    conn = get_connection()
    conn.execute("UPDATE reminders SET is_read=1 WHERE id=?", (reminder_id,))
    conn.commit()
    conn.close()


def get_unread_reminder_count(student_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM reminders WHERE student_id=? AND is_read=0",
        (student_id,)
    ).fetchone()
    conn.close()
    return row["cnt"] if row else 0


# ── Teacher analytics ──

def get_students_by_institution(institution_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM students WHERE institution_id=? ORDER BY full_name",
        (institution_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_audit_log(limit=50):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Seed demo data ──

def seed_demo_data():
    conn = get_connection()
    institutions = [
        ("St Mary's Academy", "London", "United Kingdom", "school"),
        ("City Sixth Form College", "Manchester", "United Kingdom", "college"),
        ("Greenwood University", "Birmingham", "United Kingdom", "university"),
        ("North London Grammar School", "London", "United Kingdom", "school"),
        ("Bristol FE College", "Bristol", "United Kingdom", "college"),
        ("Sheffield Hallam University", "Sheffield", "United Kingdom", "university"),
    ]
    for name, city, country, itype in institutions:
        try:
            conn.execute(
                "INSERT INTO institutions (name, city, country, institution_type) VALUES (?,?,?,?)",
                (name, city, country, itype)
            )
        except sqlite3.IntegrityError:
            pass
    conn.commit()

    def seed_courses(inst_name, courses):
        inst = conn.execute("SELECT id FROM institutions WHERE name=?", (inst_name,)).fetchone()
        if inst:
            iid = inst["id"]
            if not conn.execute("SELECT id FROM courses WHERE institution_id=?", (iid,)).fetchone():
                for t, q, l, d in courses:
                    conn.execute(
                        "INSERT INTO courses (institution_id, title, qualification, level, description) VALUES (?,?,?,?,?)",
                        (iid, t, q, l, d)
                    )

    seed_courses("City Sixth Form College", [
        ("Mathematics", "A-Level", "Year 12/13", "Pure Maths, Statistics, Mechanics"),
        ("Computer Science", "A-Level", "Year 12/13", "Algorithms, OOP, Databases"),
        ("Physics", "A-Level", "Year 12/13", "Mechanics, Electricity, Quantum"),
        ("Psychology", "A-Level", "Year 12/13", "Biopsychology, Social, Cognitive"),
        ("Business Studies", "BTEC Level 3", "Year 12/13", "Finance, Marketing, HR"),
        ("Software Development", "T-Level", "Year 12/13", "Full-stack, agile, placement"),
    ])
    seed_courses("Greenwood University", [
        ("Computer Science BSc", "Bachelor's Degree", "Year 1–3", "Software engineering, AI, databases"),
        ("Data Science BSc", "Bachelor's Degree", "Year 1–3", "Statistics, ML, Python, big data"),
        ("Business Management BA", "Bachelor's Degree", "Year 1–3", "Strategy, finance, marketing"),
        ("Psychology BSc", "Bachelor's Degree", "Year 1–3", "Research, clinical, social"),
        ("Engineering MEng", "Integrated Master's", "Year 1–5", "Mechanical, civil, electrical"),
        ("Nursing BSc", "Bachelor's Degree", "Year 1–3", "Clinical placements, pharmacology"),
    ])
    seed_courses("St Mary's Academy", [
        ("Mathematics", "GCSE", "Year 10/11", "Number, algebra, geometry, statistics"),
        ("English Language", "GCSE", "Year 10/11", "Reading, writing, speaking"),
        ("English Literature", "GCSE", "Year 10/11", "Shakespeare, prose, poetry"),
        ("Science (Combined)", "GCSE", "Year 10/11", "Biology, chemistry, physics"),
        ("History", "GCSE", "Year 10/11", "Cold War, Germany, medicine"),
        ("ICT", "GCSE", "Year 10/11", "Spreadsheets, databases, coding"),
    ])

        # Add generic demo courses if database is empty
    existing = conn.execute(
        "SELECT COUNT(*) as count FROM courses"
    ).fetchone()["count"]

    if existing == 0:

        demo_courses = [

            ("GCSE Mathematics", "GCSE", "Year 10"),
            ("GCSE English Literature", "GCSE", "Year 11"),
            ("GCSE Biology", "GCSE", "Year 11"),
            ("AS-Level Physics", "AS-Level", "Year 12"),
            ("A-Level Mathematics", "A-Level", "Year 13"),
            ("A-Level Computer Science", "A-Level", "Year 13"),
            ("BTEC Business Studies", "BTEC Level 3", "Level 3"),
            ("BTEC Information Technology", "BTEC Level 3", "Level 3"),
            ("T-Level Digital Production", "T-Level", "Level 3"),
            ("Access to HE Nursing", "Access to HE", "Foundation"),
            ("Foundation Computer Science", "Foundation Degree", "Year 1"),
            ("BSc Artificial Intelligence", "Bachelor's Degree", "Year 1"),
            ("BSc Data Science", "Bachelor's Degree", "Year 2"),
            ("MSc Machine Learning", "Master's Degree", "Postgraduate"),
            ("MBA Business Analytics", "Master's Degree", "Postgraduate")

        ]

        for title, qualification, level in demo_courses:

            conn.execute(
                """
                INSERT INTO courses (
                    institution_id,
                    title,
                    qualification,
                    level,
                    description
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    1,
                    title,
                    qualification,
                    level,
                    f"{title} course for students."
                )
            )

    conn.commit()
    conn.close()