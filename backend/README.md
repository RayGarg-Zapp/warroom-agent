# WarRoom Agent -- Backend

AI-powered incident coordination backend that ingests alerts (Slack messages, webhooks), classifies severity with an LLM, matches against a known-issue database, plans remediation actions, and -- after human approval -- executes them through integration adapters (Zoom, Google Calendar, Slack, Email).

---

## Architecture overview

```
                           +---------------------------+
                           |     Slack / Webhooks      |
                           +------------+--------------+
                                        |
                                   Ingest layer
                                        |
                           +------------v--------------+
                           |   LangGraph  Workflow     |
                           |                           |
                           |  +---------+  +---------+ |
                           |  |Classify |->|Resolve  | |
                           |  +---------+  +---------+ |
                           |       |            |      |
                           |  +----v----+  +----v----+ |
                           |  | Match   |->|  Plan   | |
                           |  +---------+  +---------+ |
                           |                   |       |
                           |          +--------v-----+ |
                           |          |Approval Gate | |
                           |          +--------+-----+ |
                           |                   |       |
                           |          +--------v-----+ |
                           |          |   Execute    | |
                           |          +--------------+ |
                           +------------+--------------+
                                        |
                     +------------------+------------------+
                     |                  |                   |
              +------v------+   +------v------+   +-------v------+
              | Zoom Adapter|   |Slack Adapter|   |Calendar/Email|
              +------+------+   +------+------+   +-------+------+
                     |                  |                   |
                     +--------+---------+-------------------+
                              |
                    +---------v----------+
                    | Auth0 Token Vault  |
                    +--------------------+
```

**Key components:**

| Layer | Technology | Location |
|---|---|---|
| HTTP API | FastAPI | `app/api/` |
| AI Workflow | LangGraph + Anthropic Claude | `app/agents/` |
| Data layer | SQLAlchemy (SQLite default, Postgres-ready) | `app/models/`, `app/database.py` |
| Integration adapters | httpx, smtplib | `app/integrations/` |
| Security | Auth0 Token Vault, JWT, Execution Guard | `app/security/`, `app/integrations/auth0_service.py` |

---

## Quick start

```bash
# 1. Navigate to the backend directory
cd backend

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY for LLM features

# 5. Seed the database with demo data
python -m scripts.seed_data

# 6. Start the development server
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.
Interactive docs at `http://localhost:8000/docs`.

---

## API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Root -- service info |
| `GET` | `/health` | Health check |
| **Incidents** | | |
| `GET` | `/api/incidents` | List all incidents |
| `GET` | `/api/incidents/{incident_id}` | Get incident details |
| `POST` | `/api/incidents/inject` | Inject a raw alert message for AI processing |
| **Actions** | | |
| `GET` | `/api/actions` | List planned actions (filter by `?status=pending`) |
| `POST` | `/api/actions/{action_id}/approve` | Approve a pending action |
| `POST` | `/api/actions/{action_id}/deny` | Deny a pending action |
| `POST` | `/api/actions/{action_id}/execute` | Execute a single approved action |
| `POST` | `/api/actions/execute-all/{incident_id}` | Execute all approved actions for an incident |
| **Audit** | | |
| `GET` | `/api/audit` | View the full audit trail |
| **Integrations** | | |
| `GET` | `/api/integrations` | List integration connections |
| `POST` | `/api/integrations/{integration_id}/reconnect` | Reconnect an integration |
| `GET` | `/api/integrations/{integration_id}/status` | Check integration health |
| **Slack Webhook** | | |
| `POST` | `/api/slack/events` | Receive Slack event callbacks |
| **Demo** | | |
| `POST` | `/api/demo/seed` | Seed the database with demo data |
| `GET` | `/api/demo/health` | Demo health check |

---

## Demo workflow walkthrough

Run these steps in order to see the full incident lifecycle:

```bash
BASE=http://localhost:8000

# 1. Seed demo data (responders, known issues, integrations)
curl -X POST $BASE/api/demo/seed

# 2. Inject a P1 alert message
curl -X POST $BASE/api/incidents/inject \
  -H "Content-Type: application/json" \
  -d '{"source": "slack", "raw_message": "URGENT: payments-service is returning 500 errors across all regions. Customer checkouts are failing. Multiple PagerDuty alerts firing."}'

# 3. View the analyzed incident
curl $BASE/api/incidents

# 4. See pending approval actions
curl "$BASE/api/actions?status=pending"

# 5. Approve each pending action (replace {id} with actual IDs)
curl -X POST $BASE/api/actions/{id}/approve
curl -X POST $BASE/api/actions/{id}/approve

# 6. Execute all approved actions for the incident
curl -X POST $BASE/api/actions/execute-all/{incident_id}

# 7. View the full audit trail
curl $BASE/api/audit
```

---

## Docker usage

**Build and run with Docker Compose (recommended for local dev):**

```bash
docker compose up --build
```

**Build and run standalone:**

```bash
docker build -t warroom-backend .
docker run -p 8000:8000 --env-file .env warroom-backend
```

To switch to PostgreSQL, uncomment the `postgres` service in `docker-compose.yml` and update `DATABASE_URL` in your `.env`:

```
DATABASE_URL=postgresql://warroom:warroom@postgres:5432/warroom
```

---

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | No | `sqlite:///./warroom.db` | Database connection string |
| `ANTHROPIC_API_KEY` | Yes (for LLM) | `""` | Anthropic API key for Claude-powered classification and planning |
| `ANTHROPIC_MODEL` | No | `claude-sonnet-4-5` | Anthropic Claude model ID |
| `SLACK_BOT_TOKEN` | No | `""` | Slack Bot OAuth token |
| `SLACK_SIGNING_SECRET` | No | `""` | Slack request signing secret |
| `ZOOM_CLIENT_ID` | No | `""` | Zoom OAuth client ID |
| `ZOOM_CLIENT_SECRET` | No | `""` | Zoom OAuth client secret |
| `ZOOM_ACCOUNT_ID` | No | `""` | Zoom account ID |
| `GOOGLE_SERVICE_ACCOUNT_KEY` | No | `""` | Google service account JSON key (as string) |
| `SMTP_HOST` | No | `""` | SMTP server hostname |
| `SMTP_PORT` | No | `587` | SMTP server port |
| `SMTP_USER` | No | `""` | SMTP username |
| `SMTP_PASS` | No | `""` | SMTP password |
| `AUTH0_DOMAIN` | No | `""` | Auth0 tenant domain |
| `AUTH0_CLIENT_ID` | No | `""` | Auth0 application client ID |
| `AUTH0_CLIENT_SECRET` | No | `""` | Auth0 application client secret |
| `AUTH0_AUDIENCE` | No | `""` | Auth0 API audience |
| `AUTH0_TOKEN_VAULT_URL` | No | `""` | Auth0 Token Vault endpoint |
| `JWT_SECRET` | No | `warroom-dev-secret-change-me` | Secret for signing JWTs |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `CORS_ORIGINS` | No | `["http://localhost:5173","http://localhost:3000"]` | Allowed CORS origins (JSON list) |
| `APP_ENV` | No | `development` | Application environment |

---

## Integration setup

Each integration adapter lives in `app/integrations/` and can run in stub mode (no credentials) or live mode.

For detailed setup guides covering OAuth flows, token refresh, and Auth0 Token Vault configuration, see:

- **[integrations/setup-guide.md](../integrations/setup-guide.md)** -- step-by-step instructions for Slack, Zoom, Google Calendar, Email, and Auth0.

---

## Known limitations

- **SQLite for MVP** -- the default database is a local SQLite file. For production use, switch to PostgreSQL via the `DATABASE_URL` environment variable.
- **No persistent background workers** -- action execution runs inline on the request thread. A task queue (Celery, Dramatiq) is recommended for production.
- **Stub integrations** -- Zoom, Calendar, and Email adapters return mock responses when credentials are not configured. They will make real API calls once valid tokens are provided.
- **Single-tenant** -- there is no multi-tenant isolation. All data shares one database.
- **No WebSocket push** -- the frontend polls for updates. A WebSocket layer would improve real-time responsiveness.
- **LLM dependency** -- incident classification and action planning require a valid `ANTHROPIC_API_KEY`. Without it, the system falls back to rule-based keyword classification (still functional).
