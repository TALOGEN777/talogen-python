"""HTTP client for the talogen.dev REST API (standard library only).

API reference: https://talogen.dev/developers/ — OpenAPI: https://talogen.dev/openapi.json
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional

DEFAULT_BASE_URL = "https://talogen.dev"

#: Every machine-readable entry point of the site, for agents that want the
#: full picture in one place (the CLI's ``links`` command prints these).
ENTRY_POINTS = {
    "api_index": "https://talogen.dev/api/v1",
    "openapi": "https://talogen.dev/openapi.json",
    "developer_portal": "https://talogen.dev/developers/",
    "llms_txt": "https://talogen.dev/llms.txt",
    "markdown_homepage": "https://talogen.dev/index.md",
    "portfolio_json": "https://talogen.dev/portfolio.json",
    "agent_manifest": "https://talogen.dev/.well-known/agent.json",
    "candidate_profile": "https://talogen.dev/.well-known/candidate.json",
    "mcp_endpoint": "https://talogen.dev/mcp",
    "mcp_discovery": "https://talogen.dev/.well-known/mcp",
    "mcp_server_card": "https://talogen.dev/.well-known/mcp/server-card.json",
    "agent_skills": "https://talogen.dev/.well-known/agent-skills/index.json",
    "ard_catalog": "https://talogen.dev/.well-known/ard.json",
    "for_hiring_agents": "https://talogen.dev/for-recruiters.html",
}


@dataclass(frozen=True)
class RateLimit:
    """RateLimit headers (draft-ietf-httpapi-ratelimit-headers) on every response."""

    limit: Optional[int]
    remaining: Optional[int]
    reset_seconds: Optional[int]
    policy: Optional[str]
    retry_after: Optional[int] = None

    @classmethod
    def from_headers(cls, headers: Any) -> "RateLimit":
        def _int(name: str) -> Optional[int]:
            v = headers.get(name)
            try:
                return int(v) if v is not None else None
            except (TypeError, ValueError):
                return None

        return cls(
            limit=_int("RateLimit-Limit"),
            remaining=_int("RateLimit-Remaining"),
            reset_seconds=_int("RateLimit-Reset"),
            policy=headers.get("RateLimit-Policy"),
            retry_after=_int("Retry-After"),
        )


class TalogenError(Exception):
    """An error response from the API (4xx/5xx) or a transport failure.

    Attributes:
        status: HTTP status (0 for transport failures).
        code: the API's machine-readable code, e.g. ``not_found``,
            ``validation_failed``, ``rate_limited``.
        message: human-readable explanation.
        hint: the API's fix-it hint, when present.
        rate_limit: RateLimit headers on the failing response.
        body: the decoded JSON body, when there was one.
    """

    def __init__(self, status: int, code: str, message: str, hint: Optional[str] = None,
                 rate_limit: Optional[RateLimit] = None, body: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(f"{status} {code}: {message}")
        self.status = status
        self.code = code
        self.message = message
        self.hint = hint
        self.rate_limit = rate_limit
        self.body = body or {}


class Client:
    """Client for the talogen.dev REST API.

    Args:
        base_url: API origin (default ``TALOGEN_BASE_URL`` or https://talogen.dev).
        timeout: per-request timeout in seconds.
        user_agent: overrides ``talogen-python/<version>``.
    """

    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0, user_agent: Optional[str] = None) -> None:
        self.base_url = (base_url or os.environ.get("TALOGEN_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        from . import __version__

        self.user_agent = user_agent or f"talogen-python/{__version__}"
        self.last_rate_limit: Optional[RateLimit] = None

    # ------------------------------------------------------------------ #

    def request(self, method: str, path: str, *, json_body: Optional[Dict[str, Any]] = None,
                params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Perform one API call and return the decoded JSON body."""
        url = self.base_url + path
        if params:
            clean = {k: v for k, v in params.items() if v is not None and v is not False}
            if clean:
                url += "?" + urllib.parse.urlencode({k: ("true" if v is True else v) for k, v in clean.items()})
        data = None
        req_headers = {"Accept": "application/json", "User-Agent": self.user_agent}
        if json_body is not None:
            data = json.dumps({k: v for k, v in json_body.items() if v is not None}).encode("utf-8")
            req_headers["Content-Type"] = "application/json"
        if headers:
            req_headers.update({k: v for k, v in headers.items() if v})
        req = urllib.request.Request(url, data=data, method=method.upper(), headers=req_headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
                self.last_rate_limit = RateLimit.from_headers(resp.headers)
                return self._decode(raw, resp.status)
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            rate = RateLimit.from_headers(exc.headers)
            self.last_rate_limit = rate
            body = self._decode(raw, exc.code, lenient=True)
            err = body.get("error")
            if isinstance(err, dict):
                code = str(err.get("code") or f"http_{exc.code}")
                message = str(err.get("message") or exc.reason or "Request failed")
                hint = err.get("hint")
            else:
                code = str(err or f"http_{exc.code}")
                message = str(body.get("message") or exc.reason or "Request failed")
                hint = body.get("hint")
            raise TalogenError(exc.code, code, message, hint=hint, rate_limit=rate, body=body) from None
        except urllib.error.URLError as exc:
            raise TalogenError(0, "network_error", str(exc.reason)) from exc

    @staticmethod
    def _decode(raw: bytes, status: int, lenient: bool = False) -> Dict[str, Any]:
        if not raw:
            return {}
        try:
            body = json.loads(raw.decode("utf-8"))
        except ValueError:
            if lenient:
                return {"error": f"http_{status}", "message": raw.decode("utf-8", "replace")[:500]}
            raise TalogenError(status, "invalid_response", "The API did not return JSON.") from None
        return body if isinstance(body, dict) else {"data": body}

    # ------------------------------------------------------------------ #
    # Reads
    # ------------------------------------------------------------------ #

    def api_index(self) -> Dict[str, Any]:
        """Endpoint directory for the REST API."""
        return self.request("GET", "/api/v1")

    def get_profile(self) -> Dict[str, Any]:
        """Profile: headline, summary, about, contact, skill categories, strengths."""
        return self.request("GET", "/api/v1/profile")

    def get_candidate(self) -> Dict[str, Any]:
        """Hiring facts: availability, target roles, location, work authorization."""
        return self.request("GET", "/api/v1/candidate")

    def list_projects(self, *, tag: Optional[str] = None, flagship: bool = False,
                      limit: Optional[int] = None, cursor: Optional[str] = None) -> Dict[str, Any]:
        """One page of project summaries (``items``, ``total``, ``next_cursor``)."""
        return self.request("GET", "/api/v1/projects", params={"tag": tag, "flagship": flagship or None, "limit": limit, "cursor": cursor})

    def list_agents(self, *, tag: Optional[str] = None, limit: Optional[int] = None,
                    cursor: Optional[str] = None) -> Dict[str, Any]:
        """One page of autonomous-agent summaries."""
        return self.request("GET", "/api/v1/agents", params={"tag": tag, "limit": limit, "cursor": cursor})

    def iter_projects(self, *, tag: Optional[str] = None, flagship: bool = False) -> Iterator[Dict[str, Any]]:
        """Every project, following cursor pagination."""
        cursor: Optional[str] = None
        while True:
            page = self.list_projects(tag=tag, flagship=flagship, limit=50, cursor=cursor)
            for item in page.get("items", []):
                yield item
            cursor = page.get("next_cursor")
            if not cursor:
                return

    def iter_agents(self, *, tag: Optional[str] = None) -> Iterator[Dict[str, Any]]:
        """Every autonomous agent, following cursor pagination."""
        cursor: Optional[str] = None
        while True:
            page = self.list_agents(tag=tag, limit=50, cursor=cursor)
            for item in page.get("items", []):
                yield item
            cursor = page.get("next_cursor")
            if not cursor:
                return

    def get_project(self, project_id: str) -> Dict[str, Any]:
        """Full problem, solution, result detail for one project or agent by id."""
        return self.request("GET", f"/api/v1/projects/{urllib.parse.quote(project_id)}")

    def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """Full detail for one autonomous agent by id."""
        return self.request("GET", f"/api/v1/agents/{urllib.parse.quote(agent_id)}")

    # ------------------------------------------------------------------ #
    # The one write
    # ------------------------------------------------------------------ #

    def contact(self, message: str, reply_to: str, *, sender: Optional[str] = None,
                subject: Optional[str] = None, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        """Send Tal a message about a role or opportunity (async job).

        Returns the ``202 Accepted`` body with ``id`` and ``status_url``; poll
        :meth:`contact_status` for the delivery record. A human reads and
        replies to ``reply_to``, which must be a real mailbox.
        """
        if not message or len(message) < 5:
            raise ValueError("message must be at least 5 characters")
        if not reply_to or "@" not in reply_to:
            raise ValueError("reply_to must be a real mailbox")
        body = {"message": message, "reply_to": reply_to, "from": sender, "subject": subject}
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        return self.request("POST", "/api/v1/contact", json_body=body, headers=headers)

    def contact_status(self, job_id: str) -> Dict[str, Any]:
        """Delivery record of a contact job (content-free)."""
        return self.request("GET", f"/api/v1/contact/{urllib.parse.quote(job_id)}")

    # ------------------------------------------------------------------ #

    def links(self) -> Dict[str, str]:
        """Every machine-readable entry point of the site."""
        return dict(ENTRY_POINTS)
