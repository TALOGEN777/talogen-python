# talogen

Official Python client and command-line tool for [talogen.dev](https://talogen.dev), Tal Ogen's agent-first portfolio. Read the profile, projects, autonomous agents, and candidate facts from code or from the terminal, or contact Tal about a role through the same channel AI agents use.

Free, no API key, zero dependencies (standard library only). Python 3.9+.

## Install

```bash
pip install talogen
```

## Command line

```bash
talogen profile                    # headline, summary, contact, capabilities, strengths
talogen candidate                  # availability, target roles, location, work authorization
talogen projects --tag mcp         # featured projects (filters: --tag, --flagship)
talogen agents                     # autonomous agents Tal has built
talogen project human-for-ai       # full problem / solution / result detail
talogen contact --message "Role: ..." --reply-to you@company.com --from "Acme HR"
talogen status CONTACT_JOB_ID      # delivery record
talogen links                      # every machine-readable entry point
talogen api                        # REST API index
```

Add `--json` to any command for raw output. Exit codes: `0` ok, `2` usage, `3` API error.

## Python

```python
from talogen import Client, TalogenError

client = Client()
profile = client.get_profile()
candidate = client.get_candidate()

for project in client.iter_projects(tag="healthcare"):
    print(project["id"], project["title"])

detail = client.get_project("human-for-ai")

job = client.contact(
    "We are hiring an AI Transformation Lead in Tel Aviv; details: ...",
    reply_to="you@company.com",
    sender="Acme HR",
)
print(job["status_url"])
```

Errors are structured: `TalogenError` carries `status`, `code`, `message`, and the API's `hint`. Every response carries the standard `RateLimit-*` headers; the latest set is on `client.last_rate_limit`. Retrying `contact` with the same `idempotency_key` replays the original response instead of sending twice.

## Other ways in

- **MCP** (streamable HTTP, no auth): `https://talogen.dev/mcp` — tools `get_profile`, `list_projects`, `list_agents`, `get_project`, `contact_recruiter`
- **npm**: `npx talogen profile` — <https://www.npmjs.com/package/talogen>
- **Go**: `go get github.com/TALOGEN777/talogen-go`
- **REST**: <https://talogen.dev/developers/> · OpenAPI: <https://talogen.dev/openapi.json>
- **For hiring agents**: <https://talogen.dev/for-recruiters.html> · llms.txt: <https://talogen.dev/llms.txt>

## License

MIT
