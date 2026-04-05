import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database import init_db
from app.api import incidents, actions, audit, integrations, slack_webhook, demo, chat
from app.services.slack_poller import start_polling
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

settings = get_settings()

app = FastAPI(
    title="WarRoom Agent API",
    description="AI-powered incident coordination backend",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(incidents.router)
app.include_router(actions.router)
app.include_router(audit.router)
app.include_router(integrations.router)
app.include_router(slack_webhook.router)
app.include_router(demo.router)
app.include_router(chat.router)


@app.on_event("startup")
async def on_startup():
    # Import all models so Base.metadata knows about every table
    import app.models.incident  # noqa: F401
    import app.models.responder  # noqa: F401
    import app.models.responder_assignment  # noqa: F401
    import app.models.known_issue  # noqa: F401
    import app.models.known_issue_match  # noqa: F401
    import app.models.planned_action  # noqa: F401
    import app.models.audit_entry  # noqa: F401
    import app.models.integration_connection  # noqa: F401

    init_db()
    logging.getLogger(__name__).info("WarRoom Agent backend started")

    # Start Slack channel poller as a background task
    asyncio.create_task(start_polling())


@app.get("/")
def root():
    return {"message": "WarRoom Agent API", "version": "1.0.0", "status": "running"}


@app.get("/health")
def health():
    return {"status": "healthy", "service": "warroom-agent"}