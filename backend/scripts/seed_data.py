"""
Seed data script for WarRoom Agent.

Loads responders and known issues from JSON files, and seeds integration
connections from a small built-in list.

Usage:
    cd backend
    source venv/bin/activate
    python -m scripts.seed_data
"""

import json
import sys
from pathlib import Path

# Ensure the backend directory is on the path so `app` is importable
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.database import init_db, SessionLocal
from app.models.responder import Responder
from app.models.known_issue import KnownIssue
from app.models.integration_connection import IntegrationConnection


SEED_DIR = BACKEND_DIR / "data" / "seed"
RESPONDERS_FILE = SEED_DIR / "responders.json"
KNOWN_ISSUES_FILE = SEED_DIR / "known_issues.json"


def load_json_file(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Required seed file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def seed_responders(db):
    """Seed responders from backend/data/seed/responders.json"""
    responders_data = load_json_file(RESPONDERS_FILE)
    seeded_count = 0

    for idx, item in enumerate(responders_data, start=1):
        responder_id = item.get("id") or f"r{idx}"

        existing = db.query(Responder).filter(Responder.id == responder_id).first()
        if existing:
            continue

        responder = Responder(
            id=responder_id,
            name=item["name"],
            email=item["email"],
            slack_user_id=item.get("slack_user_id"),
            team=item.get("team"),
            domain=item["domain"],
            role=item.get("role"),
            timezone=item.get("timezone"),
            is_on_call=item.get("is_on_call", False),
            escalation_rank=item.get("escalation_rank", 0),
            active=item.get("active", True),
        )

        db.add(responder)
        seeded_count += 1

    db.commit()
    print(f"  Seeded {seeded_count} responders from {RESPONDERS_FILE.name}.")


def seed_known_issues(db):
    """Seed known issues from backend/data/seed/known_issues.json"""
    known_issues_data = load_json_file(KNOWN_ISSUES_FILE)
    seeded_count = 0

    for idx, item in enumerate(known_issues_data, start=1):
        issue_id = item.get("id") or f"ki{idx}"

        existing = db.query(KnownIssue).filter(KnownIssue.id == issue_id).first()
        if existing:
            continue

        keywords = item.get("keywords_json", [])
        if not isinstance(keywords, list):
            keywords = []

        known_issue = KnownIssue(
            id=issue_id,
            title=item["title"],
            description=item.get("description"),
            symptoms=item.get("symptoms"),
            keywords_json=json.dumps(keywords),
            domain=item.get("domain"),
            remediation_steps=item.get("remediation_steps"),
            runbook_url=item.get("runbook_url"),
            severity_hint=item.get("severity_hint"),
            root_cause_summary=item.get("root_cause_summary"),
            last_occurrence=item.get("last_occurrence"),
        )

        db.add(known_issue)
        seeded_count += 1

    db.commit()
    print(f"  Seeded {seeded_count} known issues from {KNOWN_ISSUES_FILE.name}.")


def seed_integration_connections(db):
    """Seed integration connections from a small built-in list."""
    connections = [
        {
            "id": "int-1",
            "provider_name": "Slack",
            "icon": "MessageSquare",
            "connection_status": "connected",
            "scopes_json": ["channels:read", "chat:write", "im:write", "users:read"],
            "security_note": "OAuth 2.0 with PKCE. Tokens rotated every 12 hours.",
        },
        {
            "id": "int-2",
            "provider_name": "Zoom",
            "icon": "Video",
            "connection_status": "connected",
            "scopes_json": ["meeting:write", "meeting:read"],
            "security_note": "Server-to-Server OAuth. Scoped to meeting creation only.",
        },
        {
            "id": "int-3",
            "provider_name": "Google Calendar",
            "icon": "Calendar",
            "connection_status": "connected",
            "scopes_json": ["calendar.events.write", "calendar.events.read"],
            "security_note": "Delegated user-level event creation through Connected Accounts and Token Vault.",
        },
        {
            "id": "int-4",
            "provider_name": "Email (SMTP)",
            "icon": "Mail",
            "connection_status": "connected",
            "scopes_json": ["mail.send"],
            "security_note": "Authenticated SMTP with TLS.",
        },
        {
            "id": "int-5",
            "provider_name": "Auth0 / Token Vault",
            "icon": "Shield",
            "connection_status": "connected",
            "scopes_json": ["token:read", "token:rotate"],
            "security_note": "Provider OAuth tokens should never be stored in the app database.",
        },
        {
            "id": "int-6",
            "provider_name": "GitHub",
            "icon": "Github",
            "connection_status": "disconnected",
            "scopes_json": ["repo", "pull_requests"],
            "security_note": "Delegated repository access through Connected Accounts and Token Vault.",
        },
    ]

    seeded_count = 0

    for item in connections:
        existing = db.query(IntegrationConnection).filter(
            IntegrationConnection.id == item["id"]
        ).first()
        if existing:
            continue

        connection = IntegrationConnection(
            id=item["id"],
            provider_name=item["provider_name"],
            icon=item["icon"],
            connection_status=item["connection_status"],
            scopes_json=json.dumps(item["scopes_json"]),
            security_note=item["security_note"],
        )

        db.add(connection)
        seeded_count += 1

    db.commit()
    print(f"  Seeded {seeded_count} integration connections.")


def main():
    print("Initializing database...")

    # Import all models so tables are registered on Base.metadata
    import app.models  # noqa: F401

    init_db()

    db = SessionLocal()
    try:
        print("Seeding data...")
        seed_responders(db)
        seed_known_issues(db)
        seed_integration_connections(db)
        print("Done! Seed data loaded successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    main()