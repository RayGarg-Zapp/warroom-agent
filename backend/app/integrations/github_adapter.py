from __future__ import annotations

import base64
import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class GitHubAdapter:
    """
    GitHub integration adapter for delegated repo remediation.

    This adapter uses a GitHub user access token obtained through Auth0 Token Vault
    and performs a direct file create/update in a target repository.

    TEMP DEBUG ADDED:
    - Proves which GitHub user the token belongs to
    - Proves whether that token can see the target repo
    - Then attempts the contents read/update
    """

    API_BASE = "https://api.github.com"

    def _load_metadata(self, action) -> dict[str, Any]:
        raw = action.metadata_json or "{}"
        if isinstance(raw, dict):
            return raw
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def _split_repo(self, repo: str) -> tuple[str, str]:
        if not repo or "/" not in repo:
            raise ValueError("repo metadata must be in the format 'owner/repo'")
        owner, name = repo.split("/", 1)
        return owner, name

    def _normalize_content(self, desired_content: Any) -> str:
        if isinstance(desired_content, (dict, list)):
            return json.dumps(desired_content, indent=2) + "\n"
        return str(desired_content)

    def update_file(
        self,
        action,
        access_token: str | None = None,
        token_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not access_token:
            return {"success": False, "error": "Missing GitHub access token"}

        metadata = self._load_metadata(action)
        repo = metadata.get("repo")
        file_path = metadata.get("file_path")
        desired_content = metadata.get("desired_content")
        commit_message = metadata.get("commit_message") or action.title
        branch = metadata.get("branch")

        if not repo:
            return {"success": False, "error": "Missing metadata.repo"}
        if not file_path:
            return {"success": False, "error": "Missing metadata.file_path"}
        if desired_content is None:
            return {"success": False, "error": "Missing metadata.desired_content"}

        owner, repo_name = self._split_repo(repo)
        normalized_content = self._normalize_content(desired_content)

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        repo_url = f"{self.API_BASE}/repos/{owner}/{repo_name}"
        contents_url = f"{self.API_BASE}/repos/{owner}/{repo_name}/contents/{file_path}"

        sha = None
        previous_content = None

        try:
            logger.info(
                "[GITHUB EXECUTION] action_id=%s repo=%s path=%s token_provider=%s token_connection=%s token_user_id=%s token_actor_email=%s",
                getattr(action, "id", None),
                repo,
                file_path,
                token_context.get("provider") if token_context else "github",
                token_context.get("connection") if token_context else None,
                token_context.get("user_id") if token_context else None,
                token_context.get("actor_email") if token_context else None,
            )

            with httpx.Client(timeout=20.0) as client:
                #
                # DEBUG 1: prove which GitHub user this Token Vault token belongs to
                #
                whoami_resp = client.get(f"{self.API_BASE}/user", headers=headers)
                logger.info(
                    "[GITHUB DEBUG] whoami status=%s body=%s",
                    whoami_resp.status_code,
                    whoami_resp.text[:500],
                )

                #
                # DEBUG 2: prove whether that token can see the target repo at all
                #
                repo_resp = client.get(repo_url, headers=headers)
                logger.info(
                    "[GITHUB DEBUG] repo_check repo=%s status=%s body=%s",
                    repo,
                    repo_resp.status_code,
                    repo_resp.text[:500],
                )

                if repo_resp.status_code != 200:
                    body = repo_resp.text[:1000]
                    logger.error(
                        "[GITHUB] repo visibility/access check failed repo=%s status=%s body=%s",
                        repo,
                        repo_resp.status_code,
                        body,
                    )
                    expected_auth_failure = repo_resp.status_code in (403, 404)
                    return {
                        "success": False,
                        "provider": "github",
                        "repo": repo,
                        "file_path": file_path,
                        "error": "GitHub denied repository visibility/access"
                        if expected_auth_failure
                        else f"GitHub repo check failed: {repo_resp.status_code}",
                        "details": body,
                        "authz_expected_failure": expected_auth_failure,
                        "debug": {
                            "whoami_status": whoami_resp.status_code,
                            "repo_check_status": repo_resp.status_code,
                        },
                    }

                #
                # Actual file read
                #
                get_params = {"ref": branch} if branch else None
                get_resp = client.get(contents_url, headers=headers, params=get_params)

                logger.info(
                    "[GITHUB DEBUG] contents_check repo=%s path=%s status=%s body=%s",
                    repo,
                    file_path,
                    get_resp.status_code,
                    get_resp.text[:500],
                )

                if get_resp.status_code == 200:
                    existing = get_resp.json()
                    sha = existing.get("sha")
                    raw_content = existing.get("content", "")
                    if raw_content:
                        decoded = base64.b64decode(raw_content).decode("utf-8")
                        previous_content = decoded
                        if decoded == normalized_content:
                            return {
                                "success": True,
                                "operation": "noop",
                                "provider": "github",
                                "repo": repo,
                                "file_path": file_path,
                                "message": "Target file already matches desired content",
                                "token_context": {
                                    "provider": token_context.get("provider") if token_context else "github",
                                    "connection": token_context.get("connection") if token_context else None,
                                },
                                "debug": {
                                    "whoami_status": whoami_resp.status_code,
                                    "repo_check_status": repo_resp.status_code,
                                    "contents_check_status": get_resp.status_code,
                                },
                            }

                elif get_resp.status_code not in (404,):
                    body = get_resp.text[:1000]
                    logger.error(
                        "[GITHUB] failed to read file repo=%s path=%s status=%s body=%s",
                        repo,
                        file_path,
                        get_resp.status_code,
                        body,
                    )
                    return {
                        "success": False,
                        "provider": "github",
                        "repo": repo,
                        "file_path": file_path,
                        "error": f"Failed to read target file: {get_resp.status_code}",
                        "details": body,
                        "debug": {
                            "whoami_status": whoami_resp.status_code,
                            "repo_check_status": repo_resp.status_code,
                            "contents_check_status": get_resp.status_code,
                        },
                    }

                #
                # Actual file create/update
                #
                put_payload: dict[str, Any] = {
                    "message": commit_message,
                    "content": base64.b64encode(normalized_content.encode("utf-8")).decode("utf-8"),
                }
                if sha:
                    put_payload["sha"] = sha
                if branch:
                    put_payload["branch"] = branch

                put_resp = client.put(contents_url, headers=headers, json=put_payload)

                logger.info(
                    "[GITHUB DEBUG] put_check repo=%s path=%s status=%s body=%s",
                    repo,
                    file_path,
                    put_resp.status_code,
                    put_resp.text[:500],
                )

                if put_resp.status_code not in (200, 201):
                    body = put_resp.text[:1000]
                    logger.error(
                        "[GITHUB] failed to update file repo=%s path=%s status=%s body=%s",
                        repo,
                        file_path,
                        put_resp.status_code,
                        body,
                    )
                    expected_auth_failure = put_resp.status_code in (403, 404)
                    return {
                        "success": False,
                        "provider": "github",
                        "repo": repo,
                        "file_path": file_path,
                        "error": "GitHub denied the requested repository action"
                        if expected_auth_failure
                        else f"GitHub file update failed: {put_resp.status_code}",
                        "details": body,
                        "authz_expected_failure": expected_auth_failure,
                        "debug": {
                            "whoami_status": whoami_resp.status_code,
                            "repo_check_status": repo_resp.status_code,
                            "contents_check_status": get_resp.status_code,
                            "put_check_status": put_resp.status_code,
                        },
                    }

                data = put_resp.json()
                commit = data.get("commit", {}) or {}
                content = data.get("content", {}) or {}

                return {
                    "success": True,
                    "operation": "update" if sha else "create",
                    "provider": "github",
                    "repo": repo,
                    "file_path": file_path,
                    "branch": branch or content.get("path"),
                    "commit_sha": commit.get("sha"),
                    "commit_url": commit.get("html_url"),
                    "content_url": content.get("html_url"),
                    "message": commit_message,
                    "previous_content": previous_content,
                    "new_content": normalized_content,
                    "token_context": {
                        "provider": token_context.get("provider") if token_context else "github",
                        "connection": token_context.get("connection") if token_context else None,
                    },
                    "debug": {
                        "whoami_status": whoami_resp.status_code,
                        "repo_check_status": repo_resp.status_code,
                        "contents_check_status": get_resp.status_code,
                        "put_check_status": put_resp.status_code,
                    },
                }

        except Exception as exc:
            logger.exception("[GITHUB] unexpected exception during repo remediation")
            return {
                "success": False,
                "provider": "github",
                "repo": repo,
                "file_path": file_path,
                "error": str(exc),
            }
