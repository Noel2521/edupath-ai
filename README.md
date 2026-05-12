# EduPath AI v2

AI-powered student learning intelligence platform for UK schools and colleges.

## What's New in v2

- **No sidebar** — all navigation lives in the main page with a clean tab system
- **Separate Student & Teacher logins** — completely isolated portals
- **Institution & Course Management** — teachers add A-Levels, BTECs, T-Levels, Degrees to their institution
- **Multi-week plans** — 2, 4, 6, 8, or 12-week personalised study plans (UK curriculum aligned)
- **Automated weekly reminders** — auto-scheduled when a plan is generated
- **Weekly Check-ins** — students log progress each week; teachers see history
- **Proper SQLite database** — 8 tables with foreign keys and cascading deletes
- **Separated UI** — all templates in `templates/`, all CSS/JS in `static/`; `app.py` is routes only

## Project Structure

```
edupath-v2/
├── app.py                  # Flask routes (no UI logic)
├── requirements.txt
├── .env.example
├── core/
│   ├── database.py         # All DB tables, queries, helpers
│   └── ai_engine.py        # OpenAI integration + report generation
├── templates/
│   ├── base.html           # Shared layout + nav
│   ├── index.html          # Landing page
│   ├── student_login.html
│   ├── student_register.html
│   ├── student_dashboard.html
│   ├── teacher_login.html
│   ├── teacher_register.html
│   ├── teacher_dashboard.html
│   ├── plan_detail.html         # Student plan view + check-in form
│   └── plan_detail_teacher.html # Teacher read-only plan view
├── static/
│   ├── css/main.css        # Full design system (forest green + amber)
│   └── js/main.js          # Tabs, range sliders, markdown renderer
└── data/
    └── edupath.db          # SQLite database (auto-created)
```

## Database Schema

| Table | Purpose |
|---|---|
| `institutions` | Schools, colleges, universities |
| `courses` | Subjects/qualifications per institution |
| `teachers` | Teacher accounts (separate from students) |
| `students` | Student accounts |
| `enrolments` | Student ↔ Course relationships |
| `learning_plans` | AI-generated plans with risk scores |
| `weekly_checkins` | Student progress submissions |
| `reminders` | Auto-scheduled weekly reminders |

## Setup

```bash
# 1. Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your OpenAI API key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 4. Run
python app.py
```

Open http://localhost:5000

A demo institution "Demo College UK" is seeded automatically with 6 courses.

## UK Curriculum Support

Plans are generated with knowledge of:
- GCSE (Foundation & Higher)
- AS-Level / A-Level
- BTEC Level 2 & 3
- T-Levels
- Access to Higher Education
- Undergraduate Degrees (Year 1–3)
- Postgraduate

Resources suggested include BBC Bitesize, Seneca, Corbettmaths, GCSE Pod, and more.
