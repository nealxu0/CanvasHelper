# utils/canvas_parser.py

import re
from datetime import datetime

def clean_html(raw_html: str) -> str:
    """
    Removes HTML tags from assignment descriptions.
    """
    return re.sub(r'<.*?>', '', raw_html or '')

def format_due_date(due_str: str) -> str:
    """
    Converts ISO date (from Canvas) into readable string.
    """
    if not due_str:
        return "No due date"
    try:
        dt = datetime.fromisoformat(due_str.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y %I:%M %p")
    except Exception:
        return "Invalid date"

def parse_canvas_assignment(raw: dict) -> dict:
    """
    Cleans and standardizes one Canvas assignment object.
    """
    return {
        "course": raw.get("course_name", "Unknown"),
        "name": raw.get("name", "No Title"),
        "due_date": format_due_date(raw.get("due_at")),
        "description": clean_html(raw.get("description", "")),
    }

def summarize_assignments(assignments: list) -> str:
    """
    Turns a list of assignments into one readable block of text
    for an AI model to summarize or plan from.
    """
    lines = []
    for a in assignments:
        lines.append(
            f"{a['course']} - {a['name']} (Due: {a['due_date']}): {a['description']}"
        )
    return "\n".join(lines)
