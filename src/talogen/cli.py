"""``talogen`` — read Tal Ogen's portfolio from the terminal.

    talogen profile
    talogen candidate
    talogen services
    talogen analyze "the workflow: what happens, who does it, how often, which tools"
    talogen cases "a problem or a capability" [--limit 5]
    talogen projects [--tag mcp] [--flagship]
    talogen agents [--tag ...]
    talogen project human-for-ai
    talogen contact --message "..." --reply-to you@example.com [--from ...] [--subject ...]
    talogen status CONTACT_JOB_ID
    talogen links
    talogen api

Add ``--json`` for raw JSON. ``TALOGEN_BASE_URL`` is honoured.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, List, Optional

from . import __version__
from .client import Client, TalogenError

EXIT_OK, EXIT_USAGE, EXIT_API_ERROR = 0, 2, 3


def _print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def _kv(label: str, value: Any) -> None:
    if value in (None, "", [], {}):
        return
    print(f"{label:<18}{value}")


def _text(value: Any) -> str:
    """Paragraph fields arrive as a string or a list of strings."""
    if isinstance(value, list):
        return "\n\n".join(str(v) for v in value)
    return "" if value is None else str(value)


def cmd_profile(client: Client, args: argparse.Namespace) -> int:
    p = client.get_profile()
    if args.json:
        _print_json(p)
        return EXIT_OK
    print(f"{p.get('name')} — {p.get('headline')}\n")
    if p.get("tagline"):
        print(_text(p["tagline"]) + "\n")
    if p.get("summary"):
        print(_text(p["summary"]) + "\n")
    contact = p.get("contact") or {}
    for k in ("email", "linkedin", "github"):
        _kv(k, contact.get(k))
    _kv("website", p.get("website"))
    cats = p.get("skillCategories") or []
    if cats:
        print("\nCapabilities:")
        for c in cats:
            name = c.get("category") or c.get("name") or c.get("title") or ""
            items = c.get("items") or c.get("skills") or []
            print(f"  {name}: {', '.join(map(str, items))[:160]}")
    if p.get("strengths"):
        print("\nStrengths:")
        for s in p["strengths"]:
            if isinstance(s, dict):
                print(f"  - {s.get('title')}: {_text(s.get('detail'))}")
            else:
                print(f"  - {s}")
    return EXIT_OK


def cmd_candidate(client: Client, args: argparse.Namespace) -> int:
    c = client.get_candidate()
    if args.json:
        _print_json(c)
        return EXIT_OK
    _kv("name", c.get("name"))
    _kv("headline", c.get("headline"))
    _kv("availability", c.get("availability"))
    _kv("location", c.get("location"))
    _kv("work_auth", c.get("work_authorization"))
    langs = c.get("languages")
    _kv("languages", ", ".join(map(str, langs)) if isinstance(langs, list) else langs)
    roles = c.get("target_roles")
    if roles:
        print("target_roles:")
        for r in roles if isinstance(roles, list) else [roles]:
            print(f"  - {r}")
    _kv("compensation", c.get("compensation"))
    if c.get("summary"):
        print("\n" + _text(c["summary"]))
    return EXIT_OK


def cmd_services(client: Client, args: argparse.Namespace) -> int:
    s = client.get_services()
    if args.json:
        _print_json(s)
        return EXIT_OK
    print(f"{s.get('name')}\n")
    for key in ("promise", "approach", "positioning"):
        if s.get(key):
            print(_text(s[key]) + "\n")
    print("Engagement stages:")
    for st in s.get("stages") or []:
        line = f"  {st.get('step')}. {st.get('name')} - {_text(st.get('summary'))}"
        if st.get("identifies"):
            line += " Identifies: " + ", ".join(map(str, st["identifies"])) + "."
        print(line)
    if s.get("useCases"):
        print("\nProblems this solves (representative examples, not client claims):")
        for u in s["useCases"]:
            print(f"  {u.get('title')} -> {_text(u.get('outcome'))}")
    caps = s.get("capabilities") or {}
    if caps:
        print("\nCapabilities:")
        for c in caps.values():
            if isinstance(c, dict):
                print(f"  {c.get('name')}: {', '.join(map(str, c.get('items') or []))}")
    if s.get("not_offered"):
        print("\nNot offered: " + "; ".join(map(str, s["not_offered"])).replace("; ", " | "))
    _kv("pricing", s.get("pricing"))
    print("\nNext: talogen analyze \"<your workflow>\"")
    return EXIT_OK


def cmd_analyze(client: Client, args: argparse.Namespace) -> int:
    try:
        a = client.analyze_business_problem(args.problem, industry=args.industry, team_size=args.team_size, tools=args.tools)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    if args.json:
        _print_json(a)
        return EXIT_OK
    print(f"Fit: {a.get('fit')} - {_text(a.get('fit_explanation'))}\n")
    for o in a.get("matched_opportunities") or []:
        print(f"{o.get('rank')}. {o.get('title')} (value {o.get('expected_value')}, difficulty {o.get('implementation_difficulty')})")
        print(f"   {_text(o.get('likely_approach'))}")
    pilot = a.get("recommended_first_pilot")
    if isinstance(pilot, dict):
        print(f"\nFirst pilot ({pilot.get('opportunity')}): {_text(pilot.get('pilot'))}")
    cases = a.get("relevant_case_studies") or []
    if cases:
        print("\nClosest case studies: " + ", ".join(str(c.get("id")) for c in cases))
    scope = a.get("indicative_scope") or {}
    if scope:
        print(f"\nScope: {scope.get('size')} - {_text(scope.get('size_meaning'))}")
    for c in a.get("considerations") or []:
        print(f"  - {c}")
    if a.get("disclaimer"):
        print("\n" + _text(a["disclaimer"]))
    print("Next: talogen contact --message \"<business + workflow>\" --reply-to you@company.com --subject \"AI opportunity call\"")
    return EXIT_OK


def cmd_cases(client: Client, args: argparse.Namespace) -> int:
    try:
        r = client.get_relevant_case_studies(args.query, limit=args.limit)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    if args.json:
        _print_json(r)
        return EXIT_OK
    cases = r.get("case_studies") or []
    print(f"{len(cases)} case studies for: {r.get('query')}\n")
    for c in cases:
        flag = " (flagship)" if c.get("flagship") else ""
        print(f"{c.get('id'):<38}{c.get('title')}{flag}  [score {c.get('relevance_score')}]")
        print(f"{'':<38}{_text(c.get('why_relevant'))[:140]}")
    if r.get("note"):
        print("\n" + _text(r["note"]))
    return EXIT_OK


def _print_items(items: List[dict]) -> None:
    for it in items:
        flag = " (flagship)" if it.get("flagship") else ""
        print(f"{it.get('id'):<38}{it.get('title')}{flag}")
        if it.get("problem"):
            print(f"{'':<38}{_text(it['problem'])[:110]}")


def cmd_projects(client: Client, args: argparse.Namespace) -> int:
    items = list(client.iter_projects(tag=args.tag, flagship=args.flagship))
    if args.json:
        _print_json(items)
        return EXIT_OK
    print(f"{len(items)} projects\n")
    _print_items(items)
    return EXIT_OK


def cmd_agents(client: Client, args: argparse.Namespace) -> int:
    items = list(client.iter_agents(tag=args.tag))
    if args.json:
        _print_json(items)
        return EXIT_OK
    print(f"{len(items)} autonomous agents\n")
    _print_items(items)
    return EXIT_OK


def cmd_project(client: Client, args: argparse.Namespace) -> int:
    p = client.get_project(args.id)
    if args.json:
        _print_json(p)
        return EXIT_OK
    print(f"{p.get('title')}  [{p.get('id')}]{'  (flagship)' if p.get('flagship') else ''}")
    _kv("link", p.get("link"))
    _kv("tags", ", ".join(map(str, p.get("tags") or [])))
    for section, label in (("problem", "PROBLEM"), ("my_role", "MY ROLE"), ("solution", "SOLUTION"),
                           ("ai_technical_approach", "AI & TECHNICAL APPROACH"), ("implementation", "IMPLEMENTATION"),
                           ("outcome", "OUTCOME")):
        value = p.get(section) or (p.get("result") if section == "outcome" else None)
        if value:
            print(f"\n{label}\n{_text(value)}")
    return EXIT_OK


def cmd_contact(client: Client, args: argparse.Namespace) -> int:
    try:
        r = client.contact(args.message, args.reply_to, sender=args.sender, subject=args.subject, idempotency_key=args.idempotency_key)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    if args.json:
        _print_json(r)
        return EXIT_OK
    print("Message accepted — a human reads and replies to your reply-to address.\n")
    _kv("id", r.get("id"))
    _kv("status", r.get("status"))
    _kv("status_url", r.get("status_url"))
    if r.get("message"):
        print("\n" + str(r["message"]))
    return EXIT_OK


def cmd_status(client: Client, args: argparse.Namespace) -> int:
    r = client.contact_status(args.id)
    if args.json:
        _print_json(r)
    else:
        for k in ("id", "status", "created_at", "delivered_at", "error", "message"):
            _kv(k, r.get(k))
    return EXIT_OK


def cmd_links(client: Client, args: argparse.Namespace) -> int:
    links = client.links()
    if args.json:
        _print_json(links)
    else:
        for k, v in links.items():
            print(f"{k:<20}{v}")
    return EXIT_OK


def cmd_api(client: Client, args: argparse.Namespace) -> int:
    idx = client.api_index()
    if args.json:
        _print_json(idx)
    else:
        _kv("name", idx.get("name"))
        _kv("version", idx.get("version"))
        _kv("openapi", idx.get("openapi"))
        _kv("mcp", idx.get("mcp"))
        for ep, desc in (idx.get("endpoints") or {}).items():
            print(f"  {ep:<30}{desc}")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="talogen",
        description="Tal Ogen's agent-accessible portfolio (talogen.dev) from the terminal: profile, AI transformation services, business-problem analysis, case studies, candidate facts. Free, no API key.",
        epilog="Docs: https://talogen.dev/developers/ · MCP: https://talogen.dev/mcp · Hiring agents: https://talogen.dev/for-recruiters.html",
    )
    parser.add_argument("--version", action="version", version=f"talogen {__version__}")
    parser.add_argument("--base-url", help="API origin (default $TALOGEN_BASE_URL or https://talogen.dev)")
    parser.add_argument("--timeout", type=float, default=30.0, help="per-request timeout in seconds")
    parser.add_argument("--json", action="store_true", help="print raw JSON")
    sub = parser.add_subparsers(dest="command", metavar="command")
    sub.required = True

    sub.add_parser("profile", help="headline, summary, contact, capabilities, strengths").set_defaults(func=cmd_profile)
    sub.add_parser("candidate", help="hiring facts: availability, target roles, engagement types, location, work authorization").set_defaults(func=cmd_candidate)
    sub.add_parser("services", help="AI transformation services for businesses: stages, use cases, capability pillars").set_defaults(func=cmd_services)
    p = sub.add_parser("analyze", help="can Tal help with this workflow? fit, opportunities, case studies, first pilot, scope (heuristic, not a quote)")
    p.add_argument("problem", help="the workflow: what happens, who does it, how often, which tools")
    p.add_argument("--industry")
    p.add_argument("--team-size", dest="team_size")
    p.add_argument("--tools")
    p.set_defaults(func=cmd_analyze)
    p = sub.add_parser("cases", help="case studies ranked against a problem or a capability")
    p.add_argument("query")
    p.add_argument("--limit", type=int)
    p.set_defaults(func=cmd_cases)
    p = sub.add_parser("projects", help="featured projects")
    p.add_argument("--tag")
    p.add_argument("--flagship", action="store_true")
    p.set_defaults(func=cmd_projects)
    p = sub.add_parser("agents", help="autonomous agents Tal has built")
    p.add_argument("--tag")
    p.set_defaults(func=cmd_agents)
    p = sub.add_parser("project", help="full detail for one project or agent")
    p.add_argument("id")
    p.set_defaults(func=cmd_project)
    p = sub.add_parser("contact", help="send Tal a message about a role or a business problem (a human replies)")
    p.add_argument("--message", required=True)
    p.add_argument("--reply-to", required=True, help="a real mailbox a human can reply to")
    p.add_argument("--from", dest="sender", help="who is reaching out")
    p.add_argument("--subject")
    p.add_argument("--idempotency-key")
    p.set_defaults(func=cmd_contact)
    p = sub.add_parser("status", help="delivery record of a contact job")
    p.add_argument("id")
    p.set_defaults(func=cmd_status)
    sub.add_parser("links", help="every machine-readable entry point").set_defaults(func=cmd_links)
    sub.add_parser("api", help="REST API index").set_defaults(func=cmd_api)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    client = Client(base_url=args.base_url, timeout=args.timeout)
    try:
        return int(args.func(client, args))
    except TalogenError as exc:
        if args.json:
            _print_json({"error": exc.code, "status": exc.status, "message": exc.message, "hint": exc.hint})
        else:
            print(f"error ({exc.status} {exc.code}): {exc.message}", file=sys.stderr)
            if exc.hint:
                print(f"  hint: {exc.hint}", file=sys.stderr)
        return EXIT_API_ERROR
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
