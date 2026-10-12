"""Framework integrations.

Each module only imports its optional dependency when you import it, e.g.::

    from loglens.middleware.fastapi import CorrelationIdMiddleware
    from loglens.middleware.aiohttp import correlation_middleware
"""

from __future__ import annotations
