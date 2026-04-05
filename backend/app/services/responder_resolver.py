import logging
from app.database import SessionLocal
from app.models.responder import Responder as ResponderModel

logger = logging.getLogger(__name__)


def resolve_responders(summary: str, severity: str, domains: list[str]) -> list[dict]:
    """Resolve best responders based on incident domains and severity."""

    db = SessionLocal()
    try:
        all_responders = (
            db.query(ResponderModel)
            .filter(ResponderModel.active == True)
            .all()
        )

        matched = []

        for r in all_responders:
            confidence = 0.0

            # Strong domain relevance
            if r.domain in domains:
                confidence += 0.65
                if domains and r.domain == domains[0]:
                    confidence += 0.15

            # On-call boost
            if r.is_on_call:
                confidence += 0.10

            # Lower escalation rank = more important
            if r.escalation_rank == 1:
                confidence += 0.10
            elif r.escalation_rank == 2:
                confidence += 0.05

            # Small bonus for P1 if domain is relevant
            if severity == "P1" and r.domain in domains:
                confidence += 0.05

            confidence = round(min(confidence, 0.99), 2)

            # Only include responders with meaningful relevance
            if confidence >= 0.35:
                matched.append({
                    "id": r.id,
                    "name": r.name,
                    "role": r.role or "",
                    "domain": r.domain,
                    "email": r.email,
                    "slack_user_id": r.slack_user_id,
                    "avatar": None,
                    "available": r.is_on_call,
                    "confidence": confidence
                })

        matched.sort(key=lambda x: x["confidence"], reverse=True)

        # Tighter cap for cleaner demo output
        max_responders = 5 if severity == "P1" else 4 if severity == "P2" else 3

        return matched[:max_responders]

    finally:
        db.close()