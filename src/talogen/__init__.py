"""talogen — Python client and CLI for talogen.dev, Tal Ogen's agent-first portfolio.

    from talogen import Client

    client = Client()
    profile = client.get_profile()
    page = client.list_projects(tag="healthcare")
    project = client.get_project("human-for-ai")

The API is free and unauthenticated. Reads are side-effect-free; the one write
is ``contact``, which delivers a real message to a human.
"""

from .client import DEFAULT_BASE_URL, ENTRY_POINTS, Client, TalogenError, RateLimit

__version__ = "0.1.0"

__all__ = ["Client", "TalogenError", "RateLimit", "DEFAULT_BASE_URL", "ENTRY_POINTS", "__version__"]
