"""Unit tests — no network. Run: python -m unittest discover -s tests"""

from __future__ import annotations

import io
import json
import unittest
import urllib.error
from unittest import mock

from talogen import Client, TalogenError
from talogen.cli import main


class _Resp(io.BytesIO):
    def __init__(self, status, body, headers=None):
        super().__init__(json.dumps(body).encode())
        self.status = status
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()
        return False


def _err(status, body, headers=None):
    return urllib.error.HTTPError("https://talogen.dev/x", status, "err", headers or {}, io.BytesIO(json.dumps(body).encode()))


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.c = Client(base_url="https://talogen.dev")

    def test_list_projects_builds_query(self):
        seen = {}

        def fake(req, timeout=None):
            seen["url"] = req.full_url
            return _Resp(200, {"items": [{"id": "a"}], "next_cursor": None}, {"RateLimit-Remaining": "999"})

        with mock.patch("urllib.request.urlopen", fake):
            page = self.c.list_projects(tag="mcp", flagship=True, limit=5)
        self.assertIn("tag=mcp", seen["url"])
        self.assertIn("flagship=true", seen["url"])
        self.assertIn("limit=5", seen["url"])
        self.assertEqual(page["items"][0]["id"], "a")
        self.assertEqual(self.c.last_rate_limit.remaining, 999)

    def test_iter_projects_follows_cursor(self):
        pages = iter([_Resp(200, {"items": [{"id": "a"}], "next_cursor": "c2"}), _Resp(200, {"items": [{"id": "b"}], "next_cursor": None})])
        with mock.patch("urllib.request.urlopen", lambda req, timeout=None: next(pages)):
            self.assertEqual([p["id"] for p in self.c.iter_projects()], ["a", "b"])

    def test_nested_error_object_is_parsed(self):
        e = _err(404, {"error": {"code": "not_found", "message": "No project 'x'.", "hint": "Valid ids: a, b"}})
        with mock.patch("urllib.request.urlopen", mock.Mock(side_effect=e)):
            with self.assertRaises(TalogenError) as ctx:
                self.c.get_project("x")
        self.assertEqual((ctx.exception.status, ctx.exception.code), (404, "not_found"))
        self.assertEqual(ctx.exception.hint, "Valid ids: a, b")

    def test_contact_posts_body_and_idempotency_key(self):
        seen = {}

        def fake(req, timeout=None):
            seen["body"] = json.loads(req.data.decode())
            seen["idem"] = req.get_header("Idempotency-key")
            return _Resp(202, {"id": "J1", "status": "queued", "status_url": "/api/v1/contact/J1"})

        with mock.patch("urllib.request.urlopen", fake):
            r = self.c.contact("Hello, about a role", "hr@example.com", sender="acme", idempotency_key="k1")
        self.assertEqual(r["id"], "J1")
        self.assertEqual(seen["body"]["reply_to"], "hr@example.com")
        self.assertEqual(seen["body"]["from"], "acme")
        self.assertNotIn("subject", seen["body"])
        self.assertEqual(seen["idem"], "k1")

    def test_analyze_posts_problem_and_optional_fields(self):
        seen = {}

        def fake(req, timeout=None):
            seen["url"] = req.full_url
            seen["method"] = req.get_method()
            seen["body"] = json.loads(req.data.decode())
            return _Resp(200, {"fit": "strong", "matched_opportunities": [{"id": "email-triage"}]})

        with mock.patch("urllib.request.urlopen", fake):
            a = self.c.analyze_business_problem("Two admins read 80 emails a day", industry="insurance")
        self.assertTrue(seen["url"].endswith("/api/v1/services/analyze"))
        self.assertEqual(seen["method"], "POST")
        self.assertEqual(seen["body"], {"problem": "Two admins read 80 emails a day", "industry": "insurance"})
        self.assertEqual(a["fit"], "strong")
        with self.assertRaises(ValueError):
            self.c.analyze_business_problem("short")

    def test_case_studies_builds_query(self):
        seen = {}

        def fake(req, timeout=None):
            seen["url"] = req.full_url
            return _Resp(200, {"query": "reports", "case_studies": [{"id": "qa-agent"}]})

        with mock.patch("urllib.request.urlopen", fake):
            r = self.c.get_relevant_case_studies("recurring reports", limit=3)
        self.assertIn("/api/v1/services/case-studies?", seen["url"])
        self.assertIn("q=recurring+reports", seen["url"])
        self.assertIn("limit=3", seen["url"])
        self.assertEqual(r["case_studies"][0]["id"], "qa-agent")

    def test_contact_validates_locally(self):
        with self.assertRaises(ValueError):
            self.c.contact("hi", "nope")


class CliTests(unittest.TestCase):
    def test_links_json(self):
        with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            self.assertEqual(main(["--json", "links"]), 0)
        self.assertIn("https://talogen.dev/mcp", json.loads(out.getvalue())["mcp_endpoint"])

    def test_api_error_exit_code(self):
        e = _err(404, {"error": {"code": "not_found", "message": "No project 'x'."}})
        with mock.patch("urllib.request.urlopen", mock.Mock(side_effect=e)), mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            self.assertEqual(main(["project", "x"]), 3)
        self.assertIn("not_found", err.getvalue())

    def test_analyze_renders(self):
        body = {"fit": "strong", "fit_explanation": "matches", "matched_opportunities": [{"rank": 1, "title": "Incoming emails", "expected_value": "high", "implementation_difficulty": "low", "likely_approach": "Classify and route."}], "indicative_scope": {"size": "small", "size_meaning": "One workflow."}}
        with mock.patch("urllib.request.urlopen", lambda req, timeout=None: _Resp(200, body)), mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            self.assertEqual(main(["analyze", "Two admins read 80 emails a day and update the CRM"]), 0)
        self.assertIn("Fit: strong", out.getvalue())
        self.assertIn("Incoming emails", out.getvalue())

    def test_profile_renders(self):
        body = {"name": "Tal Ogen", "headline": "Lead", "contact": {"email": "t@example.com"}, "skillCategories": [{"name": "AI", "skills": ["agents"]}]}
        with mock.patch("urllib.request.urlopen", lambda req, timeout=None: _Resp(200, body)), mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            self.assertEqual(main(["profile"]), 0)
        self.assertIn("Tal Ogen", out.getvalue())
        self.assertIn("agents", out.getvalue())


if __name__ == "__main__":
    unittest.main()
