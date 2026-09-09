"""talogen — Python client and CLI for talogen.dev, Tal Ogen's agent-first portfolio.

    from talogen import Client

    client = Client()
    profile = client.get_profile()
    services = client.get_services()
    analysis = client.analyze_business_problem("Two admins read 80 customer emails a day and update HubSpot by hand")
    page = client.list_projects(tag="human-in-the-loop")
    project = client.get_project("human-for-ai")

The API is free and unauthenticated. Reads and analysis are side-effect-free,
the one write is ``contact``, which delivers a real message to a human.
"""

from .client import DEFAULT_BASE_URL, ENTRY_POINTS, Client, TalogenError, RateLimit

__version__ = "0.2.0"

__all__ = ["Client", "TalogenError", "RateLimit", "DEFAULT_BASE_URL", "ENTRY_POINTS", "__version__"]
