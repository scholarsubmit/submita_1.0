"""
app/utils/plagiarism.py — same-assignment similarity detection.

Deliberately algorithmic, not LLM-based: comparing every submission
pair via an API call doesn't scale (a 100-student class is ~5000 pairs)
and sequence/phrase matching is actually the right tool for "did two
students write suspiciously similar text," which is a structural
question, not a judgment call an LLM is better suited for.

Runs automatically the moment a submission comes in, comparing only
against OTHER submissions for the SAME assignment (per your scoping
decision) — not a general web-search plagiarism check.
"""
import re
from difflib import SequenceMatcher


def _normalize(text):
    if not text:
        return ''
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s]', '', text)
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
                  'for', 'of', 'with', 'by', 'is', 'was', 'are', 'were'}
    words = [w for w in text.split() if w not in stop_words]
    return ' '.join(words).strip()


def _shingles(text, k=3):
    words = _normalize(text).split()
    return {' '.join(words[i:i + k]) for i in range(len(words) - k + 1)}


def _jaccard(set_a, set_b):
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return (intersection / union) * 100 if union else 0.0


def check_submission_against_peers(submission, other_submissions):
    """
    submission: the Submission being checked
    other_submissions: list of other Submission objects for the SAME assignment
    Returns (highest_score, list_of_matches) — matches sorted descending.
    """
    content = submission.content or ''
    if not content.strip():
        return 0.0, []

    norm_a = _normalize(content)
    shingles_a = _shingles(content)
    matches = []

    for other in other_submissions:
        if other.id == submission.id:
            continue
        other_content = other.content or ''
        if not other_content.strip():
            continue

        seq_score = SequenceMatcher(None, norm_a, _normalize(other_content), autojunk=False).ratio() * 100
        shingle_score = _jaccard(shingles_a, _shingles(other_content))
        combined = round((seq_score * 0.6) + (shingle_score * 0.4), 1)

        if combined > 15:  # below this, it's noise (common phrasing, not copying)
            matches.append({
                'submission_id': other.id,
                'student_name': other.student.name,
                'student_matric': other.student.matric_number,
                'similarity': combined,
                'sequence_similarity': round(seq_score, 1),
                'phrase_similarity': round(shingle_score, 1),
            })

    matches.sort(key=lambda m: m['similarity'], reverse=True)
    highest = matches[0]['similarity'] if matches else 0.0
    return highest, matches[:10]


def severity_for_score(score):
    """Returns (label, color) for a given similarity score — used consistently
    wherever a plagiarism score is displayed."""
    if score > 70:
        return 'CRITICAL', '#B42318'
    if score > 50:
        return 'HIGH', '#B54708'
    if score > 30:
        return 'MODERATE', '#B54708'
    return 'LOW', '#0F6B4C'
