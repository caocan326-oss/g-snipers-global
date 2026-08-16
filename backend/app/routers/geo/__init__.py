from fastapi import APIRouter

from app.geo_providers import GeoProviderError, provider_statuses, sample_with_provider  # noqa: F401

router = APIRouter(prefix="/api/geo", tags=["geo"])

# Submodules are imported for their side effect of registering routes on
# `router`. Import order matters only insofar as it must respect the
# dependency graph between submodules (no submodule here imports from one
# later in this list), so this is not simply alphabetical.
from . import prompts  # noqa: E402,F401
from . import sampling  # noqa: E402,F401
from . import tickets  # noqa: E402,F401
from . import assets  # noqa: E402,F401
from . import reports  # noqa: E402,F401

# Backward-compatible re-exports so `app.routers.geo.<name>` keeps working
# exactly like it did when this was a single module (tests rely on this,
# e.g. monkeypatching geo_router.sample_with_provider and expecting the
# internal caller in sampling.py to observe the patched version via the
# package-level indirection).
from .constants import (  # noqa: E402,F401
    EVIDENCE_LABELS,
    EXPORT_B2B_PACK_ID,
    EXPORT_B2B_PROMPTS,
    PROMPT_TYPES,
    PROTOCOL_VERSION,
    RECORDED_OBS,
)
