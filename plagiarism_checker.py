import re
import hashlib
from difflib import SequenceMatcher
from collections import defaultdict

class PlagiarismChecker:
    """Advanced plagiarism detection system for Submita"""

    @staticmethod
    def normalize_text(text):
        """Normalize text for comparison"""
        if not text:
            return ""
        text = text.lower()
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s]', '', text)
        # Remove common stop words to focus on meaningful content
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at',
                      'to', 'for', 'of', 'with', 'by', 'is', 'was', 'are', 'were'}
        words = text.split()
        words = [w for w in words if w not in stop_words]
        return ' '.join(words).strip()

    @staticmethod
    def get_shingles(text, k=3):
        """Generate word shingles for similarity detection"""
        normalized = PlagiarismChecker.normalize_text(text)
        words = normalized.split()
        shingles = set()
        for i in range(len(words) - k + 1):
            shingles.add(' '.join(words[i:i+k]))
        return shingles

    @staticmethod
    def calculate_jaccard_similarity(set1, set2):
        """Calculate Jaccard similarity between two sets"""
        if not set1 or not set2:
            return 0.0
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return (intersection / union) * 100 if union > 0 else 0.0

    @staticmethod
    def detect_plagiarism(current, all_submissions):
        """
        Detect plagiarism by comparing current submission with all existing ones.
        
        :param current: dict with keys 'id', 'content', 'student_name', 'student_id'
        :param all_submissions: list of dicts with same structure
        :return: list of match dicts sorted by similarity descending
        """
        results = []
        current_id = current.get('id')
        current_content = current.get('content', '')

        if not current_content or not current_content.strip():
            return []

        current_normalized = PlagiarismChecker.normalize_text(current_content)
        current_shingles = PlagiarismChecker.get_shingles(current_content)

        for other in all_submissions:
            # Skip comparing with itself
            if other.get('id') == current_id:
                continue

            other_content = other.get('content', '')
            if not other_content or not other_content.strip():
                continue

            other_normalized = PlagiarismChecker.normalize_text(other_content)
            other_shingles = PlagiarismChecker.get_shingles(other_content)

            # Sequence-based similarity (character level)
            seq_similarity = SequenceMatcher(
                None, current_normalized, other_normalized
            ).ratio() * 100

            # Shingle-based similarity (phrase level)
            shingle_similarity = PlagiarismChecker.calculate_jaccard_similarity(
                current_shingles, other_shingles
            )

            # Weighted combined score: sequence is more sensitive to rewording
            combined = (seq_similarity * 0.6) + (shingle_similarity * 0.4)

            if combined > 15:  # Only report meaningful similarities
                results.append({
                    'student_name': other.get('student_name', 'Unknown'),
                    'student_id': other.get('student_id', 'Unknown'),
                    'similarity': round(combined, 1),
                    'seq_similarity': round(seq_similarity, 1),
                    'shingle_similarity': round(shingle_similarity, 1),
                })

        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:10]

    @staticmethod
    def get_plagiarism_report(submission, matches):
        """
        Generate a structured plagiarism report.

        :param submission: Submission model object (used for metadata)
        :param matches: list from detect_plagiarism()
        :return: dict with severity, message, color, icon, recommendation, action
        """
        highest = matches[0]['similarity'] if matches else 0.0

        if highest > 70:
            severity = "CRITICAL"
            message = "⚠️ Very high similarity detected. Immediate review required before grading."
            recommendation = "This submission shares substantial content with another. Contact the student."
            action = "Do not grade without investigation"
            color = "#dc2626"
            icon = "fa-exclamation-triangle"
        elif highest > 50:
            severity = "HIGH"
            message = "⚠️ Significant similarity found. Careful review recommended."
            recommendation = "Review flagged sections and compare with matched submissions."
            action = "Request explanation or resubmission"
            color = "#f59e0b"
            icon = "fa-exclamation-circle"
        elif highest > 30:
            severity = "MODERATE"
            message = "📌 Moderate similarity detected. Some sections may need review."
            recommendation = "Check if shared content is properly cited or coincidental."
            action = "Review and decide on submission validity"
            color = "#fbbf24"
            icon = "fa-info-circle"
        else:
            severity = "LOW"
            message = "✅ Low similarity. This submission appears original."
            recommendation = "No action required. Submission looks original."
            action = "Ready for grading"
            color = "#10b981"
            icon = "fa-check-circle"

        return {
            'overall_similarity': round(highest, 1),
            'severity': severity,
            'message': message,
            'recommendation': recommendation,
            'action': action,
            'matches_count': len(matches),
            'top_matches': matches[:5],
            'severity_color': color,
            'color': color,
            'icon': icon,
        }