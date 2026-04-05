import json
import logging
import time
from functools import lru_cache
from typing import Any

import httpx
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError

from app.config import get_settings

logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer(auto_error=True)


class AuthError(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_403_FORBIDDEN):
        super().__init__(status_code=status_code, detail=detail)


class JWKSCache:
    def __init__(self):
        self.jwks: dict[str, Any] | None = None
        self.fetched_at: float = 0
        self.ttl_seconds = 60 * 10

    def is_valid(self) -> bool:
        return self.jwks is not None and (time.time() - self.fetched_at) < self.ttl_seconds

    def set(self, jwks: dict[str, Any]) -> None:
        self.jwks = jwks
        self.fetched_at = time.time()


_jwks_cache = JWKSCache()


@lru_cache(maxsize=1)
def get_auth_settings() -> dict[str, str]:
    settings = get_settings()
    domain = settings.AUTH0_DOMAIN
    audience = settings.AUTH0_AUDIENCE

    if not domain or not audience:
        raise RuntimeError("AUTH0_DOMAIN and AUTH0_AUDIENCE must be set for JWT validation")

    issuer = f"https://{domain}/"
    jwks_url = f"{issuer}.well-known/jwks.json"

    return {
        "domain": domain,
        "audience": audience,
        "issuer": issuer,
        "jwks_url": jwks_url,
    }


def get_jwks() -> dict[str, Any]:
    settings = get_auth_settings()

    if _jwks_cache.is_valid():
        return _jwks_cache.jwks  # type: ignore[return-value]

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(settings["jwks_url"])
            response.raise_for_status()
            jwks = response.json()
            _jwks_cache.set(jwks)
            return jwks
    except Exception as exc:
        logger.exception("Failed to fetch JWKS")
        raise AuthError(
            f"Unable to fetch JWKS: {str(exc)}",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def _get_signing_key(token: str) -> dict[str, Any]:
    jwks = get_jwks()
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")

    if not kid:
        raise AuthError("Token missing kid header", status.HTTP_401_UNAUTHORIZED)

    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key

    raise AuthError("Unable to find matching JWKS key", status.HTTP_401_UNAUTHORIZED)


def extract_permission_set(payload: dict[str, Any]) -> set[str]:
    permissions: set[str] = set()

    raw_scope = payload.get("scope")
    if isinstance(raw_scope, str):
        permissions.update(s.strip() for s in raw_scope.split() if s.strip())

    raw_scp = payload.get("scp")
    if isinstance(raw_scp, str):
        permissions.update(s.strip() for s in raw_scp.split() if s.strip())
    elif isinstance(raw_scp, list):
        permissions.update(str(s).strip() for s in raw_scp if str(s).strip())

    raw_permissions = payload.get("permissions")
    if isinstance(raw_permissions, list):
        permissions.update(str(p).strip() for p in raw_permissions if str(p).strip())

    return permissions


def _extract_permission_set(payload: dict[str, Any]) -> set[str]:
    return extract_permission_set(payload)


def decode_jwt_token(token: str) -> dict[str, Any]:
    settings = get_auth_settings()
    signing_key = _get_signing_key(token)

    payload = jwt.decode(
        token,
        signing_key,
        algorithms=["RS256"],
        audience=settings["audience"],
        issuer=settings["issuer"],
    )
    payload["_raw_access_token"] = token
    return payload


def verify_jwt_token(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> dict[str, Any]:
    token = credentials.credentials

    try:
        return decode_jwt_token(token)
    except ExpiredSignatureError:
        raise AuthError("Token has expired", status.HTTP_401_UNAUTHORIZED)
    except JWTClaimsError as exc:
        raise AuthError(f"Invalid token claims: {str(exc)}", status.HTTP_403_FORBIDDEN)
    except JWTError as exc:
        raise AuthError(f"Invalid token: {str(exc)}", status.HTTP_401_UNAUTHORIZED)
    except Exception as exc:
        logger.exception("Unexpected JWT validation failure")
        raise AuthError(f"Token validation failed: {str(exc)}", status.HTTP_401_UNAUTHORIZED)


def get_current_user(payload: dict[str, Any] = Depends(verify_jwt_token)) -> dict[str, Any]:
    return payload


def require_scopes(*required_scopes: str):
    def dependency(payload: dict[str, Any] = Depends(verify_jwt_token)) -> dict[str, Any]:
        granted = _extract_permission_set(payload)
        missing = [scope for scope in required_scopes if scope not in granted]

        if missing:
            debug = {
                "missing": missing,
                "granted": sorted(granted),
                "sub": payload.get("sub"),
                "aud": payload.get("aud"),
            }
            logger.warning("Permission check failed: %s", json.dumps(debug))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Forbidden. Missing required permissions: {', '.join(missing)}. "
                    f"Debug: {json.dumps(debug)}"
                ),
            )

        return payload

    return dependency
