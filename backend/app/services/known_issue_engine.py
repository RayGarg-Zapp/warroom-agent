import json
import logging
from app.database import SessionLocal
from app.models.known_issue import KnownIssue

logger = logging.getLogger(__name__)

def match_known_issues(summary: str, severity: str, domains: list[str]) -> list[dict]:
    """Match incident against known issues catalog using keyword matching."""
    db = SessionLocal()
    try:
        all_issues = db.query(KnownIssue).all()
        matches = []

        summary_lower = summary.lower()

        for issue in all_issues:
            score = 0.0

            # Domain match
            if issue.domain in domains:
                score += 0.3

            # Keyword match
            keywords = []
            if issue.keywords_json:
                try:
                    keywords = json.loads(issue.keywords_json)
                except:
                    keywords = []

            if keywords:
                keyword_hits = sum(1 for kw in keywords if kw.lower() in summary_lower)
                score += min(0.5, keyword_hits * 0.15)

            # Title/symptom similarity (simple word overlap)
            title_words = set(issue.title.lower().split())
            summary_words = set(summary_lower.split())
            overlap = len(title_words & summary_words)
            score += min(0.2, overlap * 0.05)

            if issue.symptoms:
                symptom_words = set(issue.symptoms.lower().split())
                symptom_overlap = len(symptom_words & summary_words)
                score += min(0.1, symptom_overlap * 0.03)

            score = min(round(score, 2), 0.99)

            if score >= 0.25:  # threshold
                matches.append({
                    "id": issue.id,
                    "title": issue.title,
                    "description": issue.symptoms or issue.root_cause_summary or "",
                    "matchScore": score,
                    "resolution": issue.remediation_steps or "",
                    "lastOccurrence": issue.last_occurrence or "",
                })

        matches.sort(key=lambda x: x["matchScore"], reverse=True)
        return matches[:5]
    finally:
        db.close()
