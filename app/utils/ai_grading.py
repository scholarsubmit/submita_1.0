"""
app/utils/ai_grading.py — AI-assisted grading via the Claude API.

Design principle: this NEVER writes a grade directly. It only returns a
suggestion (score + feedback + rubric breakdown) that a lecturer reviews
and explicitly accepts or edits in grade_submission(). A human is always
in the loop before anything touches a student's actual grade — this is
a deliberate safety choice, not an oversight.

If ANTHROPIC_API_KEY isn't set, or the API call fails for any reason,
this returns None and the UI falls back to plain manual grading —
AI grading being unavailable never blocks a lecturer from grading.
"""
import json

from flask import current_app

GRADING_TOOL = {
    "name": "submit_grade_assessment",
    "description": "Submit a structured grading assessment for a student submission.",
    "input_schema": {
        "type": "object",
        "properties": {
            "suggested_score": {
                "type": "number",
                "description": "Suggested score out of the assignment's total points."
            },
            "summary_feedback": {
                "type": "string",
                "description": "2-4 sentences of constructive feedback for the student, addressed to them directly."
            },
            "strengths": {
                "type": "array", "items": {"type": "string"},
                "description": "1-3 short bullet points on what the submission did well."
            },
            "weaknesses": {
                "type": "array", "items": {"type": "string"},
                "description": "1-3 short bullet points on what's missing or could improve."
            },
            "confidence": {
                "type": "string", "enum": ["low", "medium", "high"],
                "description": "How confident the assessment is, given the submission's content and clarity."
            },
        },
        "required": ["suggested_score", "summary_feedback", "strengths", "weaknesses", "confidence"],
    },
}


def get_ai_grade_suggestion(assignment, submission_content):
    """
    Returns a dict with keys: suggested_score, summary_feedback, strengths,
    weaknesses, confidence — or None if AI grading isn't available/fails.
    """
    api_key = current_app.config.get('ANTHROPIC_API_KEY')
    if not api_key:
        return None
    if not submission_content or not submission_content.strip():
        return None

    try:
        import anthropic
    except ImportError:
        current_app.logger.warning('AI grading requested but the anthropic package is not installed.')
        return None

    prompt = f"""You are grading a university assignment. Be fair, specific, and constructive.

ASSIGNMENT: {assignment.title} ({assignment.course_code} — {assignment.course_title})
TOTAL POINTS: {assignment.total_points}
INSTRUCTIONS GIVEN TO STUDENTS:
{assignment.instructions or '(no additional instructions provided)'}

STUDENT SUBMISSION:
{submission_content[:12000]}

Assess this submission against the instructions and assign a fair score out of {assignment.total_points}.
Call submit_grade_assessment with your structured assessment."""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=current_app.config.get('AI_GRADING_MODEL', 'claude-sonnet-4-5'),
            max_tokens=1024,
            tools=[GRADING_TOOL],
            tool_choice={"type": "tool", "name": "submit_grade_assessment"},
            messages=[{"role": "user", "content": prompt}],
        )

        for block in response.content:
            if block.type == 'tool_use' and block.name == 'submit_grade_assessment':
                result = dict(block.input)
                # Clamp defensively — never trust an LLM's number to be in-range unchecked.
                result['suggested_score'] = max(0, min(float(result['suggested_score']), assignment.total_points))
                return result

        return None

    except Exception as exc:
        current_app.logger.error(f'AI grading failed: {exc}')
        return None
