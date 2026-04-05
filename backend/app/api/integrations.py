import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.integration_connection import IntegrationConnection
from app.security.auth0_jwt import require_scopes

router = APIRouter(prefix="/api/integrations", tags=["integrations"])

READ_INTEGRATIONS = "read:integrations"
ADMIN_CONFIG = "admin:config"


def _serialize_integration(ic: IntegrationConnection) -> dict:
    return {
        "id": ic.id,
        "providerName": ic.provider_name,
        "icon": ic.icon or "",
        "connectionStatus": ic.connection_status,
        "scopes": json.loads(ic.scopes_json) if ic.scopes_json else [],
        "lastUsedAt": ic.last_used_at.isoformat() + "Z" if ic.last_used_at else None,
        "securityNote": ic.security_note or "",
    }


@router.get("")
def list_integrations(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_scopes(READ_INTEGRATIONS)),
):
    connections = db.query(IntegrationConnection).all()
    return {
        "data": [_serialize_integration(c) for c in connections],
        "error": None,
        "meta": {
            "total": len(connections),
            "viewer": current_user.get("email") or current_user.get("sub"),
        },
    }


@router.post("/{integration_id}/reconnect")
def reconnect_integration(
    integration_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_scopes(ADMIN_CONFIG)),
):
    conn = db.query(IntegrationConnection).filter(IntegrationConnection.id == integration_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Integration not found")

    conn.connection_status = "connected"
    db.commit()
    db.refresh(conn)

    return {"data": _serialize_integration(conn), "error": None, "meta": {}}


@router.get("/{integration_id}/status")
def check_integration_status(
    integration_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_scopes(READ_INTEGRATIONS)),
):
    conn = db.query(IntegrationConnection).filter(IntegrationConnection.id == integration_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Integration not found")

    healthy = conn.connection_status == "connected"
    return {
        "data": {
            "id": conn.id,
            "providerName": conn.provider_name,
            "healthy": healthy,
            "connectionStatus": conn.connection_status,
        },
        "error": None,
        "meta": {"viewer": current_user.get("email") or current_user.get("sub")},
    }