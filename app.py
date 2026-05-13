"""
EduPath AI — Flask Application
All routing logic. UI lives in templates/ and static/.
"""

import json
from functools import wraps
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, jsonify, flash
)
from core.database import (
    create_tables, seed_demo_data,
    register_student, login_student,
    register_teacher, login_teacher,
    get_all_institutions, add_institution,
    get_courses_by_institution, add_course, delete_course,
    save_learning_plan, get_plans_by_student, get_plan_by_id,
    save_checkin, get_checkins_by_plan,
    get_reminders_for_student, mark_reminder_read, get_unread_reminder_count,
    get_latest_plans_all, get_all_plans_for_teacher, get_students_by_institution,
)
from core.ai_engine import generate_learning_plan, extract_risk_score
import markdown
import os

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)

# ─────────── Init DB ───────────
create_tables()
seed_demo_data()


# ─────────── Auth Decorators ───────────

def student_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "student":
            return redirect(url_for("student_login"))
        return f(*args, **kwargs)
    return decorated


def teacher_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "teacher":
            return redirect(url_for("teacher_login"))
        return f(*args, **kwargs)
    return decorated


# ─────────── Landing ───────────

@app.route("/")
def index():
    return render_template("index.html")


# ─────────── Student Auth ───────────

@app.route("/student/login", methods=["GET", "POST"])
def student_login():
    if session.get("role") == "student":
        return redirect(url_for("student_dashboard"))
    error = None
    if request.method == "POST":
        student = login_student(request.form["email"], request.form["password"], request.remote_addr)
        if student:
            session["role"] = "student"
            session["user_id"] = student["id"]
            session["user_name"] = student["full_name"]
            session["institution_id"] = student["institution_id"]
            return redirect(url_for("student_dashboard"))
        error = "Invalid email or password."
    return render_template("student_login.html", error=error)


@app.route("/student/register", methods=["GET", "POST"])
def student_register():
    institutions = get_all_institutions()
    error = None
    if request.method == "POST":
        ok, msg = register_student(
            request.form["institution_id"],
            request.form["full_name"],
            request.form["email"],
            request.form["password"],
            request.form.get("year_group", ""),
            False
        )
        if ok:
            flash("Account created! Please log in.", "success")
            return redirect(url_for("student_login"))
        error = msg
    return render_template("student_register.html", institutions=institutions, error=error)


# ─────────── Teacher Auth ───────────

@app.route("/teacher/login", methods=["GET", "POST"])
def teacher_login():
    if session.get("role") == "teacher":
        return redirect(url_for("teacher_dashboard"))
    error = None
    if request.method == "POST":
        teacher = login_teacher(request.form["email"], request.form["password"],request.remote_addr)
        if teacher:
            session["role"] = "teacher"
            session["user_id"] = teacher["id"]
            session["user_name"] = teacher["full_name"]
            session["institution_id"] = teacher["institution_id"]
            return redirect(url_for("teacher_dashboard"))
        error = "Invalid email or password."
    return render_template("teacher_login.html", error=error)


@app.route("/teacher/register", methods=["GET", "POST"])
def teacher_register():
    institutions = get_all_institutions()
    error = None
    if request.method == "POST":
        ok, msg = register_teacher(
            request.form["institution_id"],
            request.form["full_name"],
            request.form["email"],
            request.form["password"]
        )
        if ok:
            flash("Account created! Please log in.", "success")
            return redirect(url_for("teacher_login"))
        error = msg
    return render_template("teacher_register.html", institutions=institutions, error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ─────────── Student Dashboard ───────────

@app.route("/student/dashboard")
@student_required
def student_dashboard():
    student_id = session["user_id"]
    plans = get_plans_by_student(student_id)
    reminders = get_reminders_for_student(student_id)
    unread = get_unread_reminder_count(student_id)
    institution_id = session.get("institution_id")
    courses = get_courses_by_institution(institution_id) if institution_id else []
    return render_template(
        "student_dashboard.html",
        plans=plans,
        reminders=reminders,
        unread_count=unread,
        courses=courses
    )


@app.route("/student/generate", methods=["POST"])
@student_required
def student_generate():
    student_id = session["user_id"]
    subject = request.form["subject"]
    level = request.form["level"]
    goal = request.form["goal"]
    struggles = request.form["struggles"]
    confidence = int(request.form.get("confidence", 50))
    study_time = request.form["study_time"]
    duration_weeks = int(request.form.get("duration_weeks", 4))
    course_id = request.form.get("course_id") or None

    report = generate_learning_plan(subject, level, goal, struggles, confidence, study_time, duration_weeks)
    risk_score = extract_risk_score(report) or 0

    plan_id = save_learning_plan(
        student_id, course_id, subject, level, goal, struggles,
        confidence, study_time, duration_weeks, report, risk_score
    )
    return redirect(url_for("view_plan", plan_id=plan_id))


@app.route("/student/plan/<int:plan_id>")
@student_required
def view_plan(plan_id):
    plan = get_plan_by_id(plan_id)
    if not plan or plan["student_id"] != session["user_id"]:
        return redirect(url_for("student_dashboard"))
    plan["report_html"] = markdown.markdown(
        plan["report"],
        extensions=["extra"]
    )
    checkins = get_checkins_by_plan(plan_id)
    return render_template("plan_detail.html", plan=plan, checkins=checkins)


@app.route("/student/checkin/<int:plan_id>", methods=["POST"])
@student_required
def submit_checkin(plan_id):
    save_checkin(
        plan_id,
        session["user_id"],
        request.form["week_number"],
        request.form.get("completed_tasks", ""),
        request.form.get("notes", ""),
        int(request.form.get("confidence", 50))
    )
    flash("Weekly check-in submitted!", "success")
    return redirect(url_for("view_plan", plan_id=plan_id))


@app.route("/student/reminder/read/<int:reminder_id>", methods=["POST"])
@student_required
def read_reminder(reminder_id):
    mark_reminder_read(reminder_id)
    return jsonify({"ok": True})


# ─────────── Teacher Dashboard ───────────

@app.route("/teacher/dashboard")
@teacher_required
def teacher_dashboard():
    institution_id = session.get("institution_id")
    all_plans = get_all_plans_for_teacher(institution_id) if institution_id else get_latest_plans_all()

    high = sum(1 for p in all_plans if (p["risk_score"] or 0) >= 70)
    medium = sum(1 for p in all_plans if 40 <= (p["risk_score"] or 0) < 70)
    low = sum(1 for p in all_plans if (p["risk_score"] or 0) < 40)

    courses = get_courses_by_institution(institution_id) if institution_id else []
    students = get_students_by_institution(institution_id) if institution_id else []
    institutions = get_all_institutions()

    return render_template(
        "teacher_dashboard.html",
        all_plans=all_plans,
        high=high, medium=medium, low=low,
        courses=courses,
        students=students,
        institutions=institutions
    )


@app.route("/teacher/plan/<int:plan_id>")
@teacher_required
def teacher_view_plan(plan_id):

    plan = get_plan_by_id(plan_id)

    plan["report_html"] = markdown.markdown(
        plan["report"],
        extensions=["extra"]
    )

    checkins = get_checkins_by_plan(plan_id)

    return render_template(
        "plan_detail_teacher.html",
        plan=plan,
        checkins=checkins
    )


# ─────────── Courses Management (Teacher) ───────────

@app.route("/teacher/courses/add", methods=["POST"])
@teacher_required
def add_course_route():
    institution_id = session.get("institution_id")
    add_course(
        institution_id,
        request.form["title"],
        request.form["qualification"],
        request.form["level"],
        request.form.get("description", "")
    )
    flash("Course added successfully.", "success")
    return redirect(url_for("teacher_dashboard"))


@app.route("/teacher/courses/delete/<int:course_id>", methods=["POST"])
@teacher_required
def delete_course_route(course_id):
    delete_course(course_id)
    flash("Course removed.", "info")
    return redirect(url_for("teacher_dashboard"))


# ─────────── Institution Management ───────────

@app.route("/teacher/institution/add", methods=["POST"])
@teacher_required
def add_institution_route():
    add_institution(request.form["name"], request.form.get("city", ""))
    flash("Institution added.", "success")
    return redirect(url_for("teacher_dashboard"))


# ─────────── API helpers ───────────

@app.route("/api/courses/<int:institution_id>")
def api_courses(institution_id):
    return jsonify(get_courses_by_institution(institution_id))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
