import httpx
from fastapi import APIRouter

router = APIRouter(prefix="/api/onsite", tags=["onsite"])

# Submodules are imported for their side effect of registering routes on
# `router`. Import order matters only insofar as it must respect the
# dependency graph between submodules (no submodule here imports from one
# later in this list), so this is not simply alphabetical.
from . import common  # noqa: E402,F401
from . import pages  # noqa: E402,F401
from . import integrations  # noqa: E402,F401
from . import diagnosis  # noqa: E402,F401
from . import crawl  # noqa: E402,F401
from . import issue_actions  # noqa: E402,F401
from . import reports  # noqa: E402,F401

# Backward-compatible re-exports so `app.routers.onsite.<name>` keeps
# working exactly like it did when this was a single module (tests rely on
# this, e.g. monkeypatching onsite_router.httpx.Client).
from .constants import INDEXNOW_ENDPOINT  # noqa: E402,F401
from .diagnosis import _fetch_brightdata_serp  # noqa: E402,F401
