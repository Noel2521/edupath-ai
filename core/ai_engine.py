"""
EduPath AI v3 — AI Engine
Generates multi-week learning plans, motivational quotes, and final-year project ideas.
"""

import os
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def generate_learning_plan(subject, level, goal, struggles, confidence, study_time, duration_weeks=4):
    prompt = f"""
You are EduPath AI — an expert academic intelligence system for UK schools, colleges, and universities.

Analyse this student profile and produce a comprehensive, structured report.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STUDENT PROFILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Subject / Course : {subject}
Academic Level   : {level}
Career / Goal    : {goal}
Current Struggles: {struggles}
Confidence Level : {confidence}%
Daily Study Time : {study_time}
Plan Duration    : {duration_weeks} weeks

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REPORT SECTIONS (follow exactly)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 1. Learning Diagnosis
- Root causes of the student's struggles (be specific, e.g. "weak algebraic manipulation")
- How these affect their progress

## 2. {duration_weeks}-Week Personalised Study Plan
For EACH week:
### Week N — [Theme Title]
**Focus:** [Main topic]
**Daily Tasks:** (based on {study_time}/day — be realistic)
**Milestone:** [What should be achieved by end of week]
**Resources:** [Specific UK resources: BBC Bitesize, Seneca, Corbettmaths, GCSE Pod, Khan Academy, etc.]

## 3. Career & Skills Gap Analysis
- Compare current skills vs what {goal} requires
- 3–5 specific skills to develop
- Map to UK qualifications or industry standards

## 4. Wellbeing & Confidence Insight
- Assess emotional wellbeing at {confidence}% confidence
- 2–3 practical mental-health / study-balance tips

## 5. Risk Assessment
- **Risk Score: XX%** (on its own line)
- Justify the score
- Identify patterns: low confidence, overload, skill mismatch, disengagement

## 6. Intervention Plan
**For the teacher:**
- [3 specific actions]

**For the student (daily habits):**
- [3 specific habits]

**Avoid:**
- [2–3 things to stop doing]

**Priority Level:** Low / Medium / High

Use UK English. Be specific, actionable, and encouraging.
"""

    response = _get_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert UK academic advisor and early-warning student risk analyst. "
                    "You deeply understand GCSEs, A-Levels, BTECs, T-Levels, Access to HE, and UK undergraduate degrees."
                )
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=3000
    )
    return response.choices[0].message.content


def generate_project_suggestions(subject, level, goal):
    """Generate 4 unique final-year project ideas for a student."""
    prompt = f"""
You are an academic supervisor for UK final-year students.

Generate EXACTLY 4 unique, creative, and practical final-year project ideas for this student:

Subject: {subject}
Level: {level}
Career Goal: {goal}

For each project return JSON with fields:
- title: short project title
- description: 2-sentence description
- difficulty: Easy / Medium / Hard
- stack: list of 3-5 tools/technologies/methods
- impact: real-world impact or relevance

Return ONLY valid JSON as an array of 4 objects. No other text.
"""
    response = _get_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert academic supervisor for UK universities and colleges."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.85,
        max_tokens=800
    )
    import json
    text = response.choices[0].message.content.strip()
    text = re.sub(r"```json|```", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        return []


def get_daily_motivation():
    """Return a motivational quote suitable for students."""
    quotes = [
        ("Success is the sum of small efforts, repeated day in and day out.", "Robert Collier"),
        ("The secret of getting ahead is getting started.", "Mark Twain"),
        ("Education is the most powerful weapon you can use to change the world.", "Nelson Mandela"),
        ("Don't watch the clock; do what it does — keep going.", "Sam Levenson"),
        ("Believe you can and you're halfway there.", "Theodore Roosevelt"),
        ("The expert in anything was once a beginner.", "Helen Hayes"),
        ("Your limitation — it's only your imagination.", "Unknown"),
        ("Push yourself, because no one else is going to do it for you.", "Unknown"),
        ("Great things never come from comfort zones.", "Unknown"),
        ("Dream it. Wish it. Do it.", "Unknown"),
        ("Hard work beats talent when talent doesn't work hard.", "Tim Notke"),
        ("It always seems impossible until it's done.", "Nelson Mandela"),
    ]
    import random
    text, author = random.choice(quotes)
    return {"quote": text, "author": author}


def extract_risk_score(report_text: str):
    match = re.search(r"Risk Score[:\s*]+(\d+)%", report_text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    match = re.search(r"\*\*(\d+)%\*\*", report_text)
    if match:
        return int(match.group(1))
    return None