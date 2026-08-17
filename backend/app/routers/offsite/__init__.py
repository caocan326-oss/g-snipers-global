from fastapi import APIRouter

router = APIRouter(prefix="/api/offsite", tags=["offsite"])

# Submodules are imported for their side effect of registering routes on
# `router`. common/constants/seeds are imported first since gaps/content/
# platforms depend on them.
from . import common  # noqa: E402,F401
from . import gaps  # noqa: E402,F401
from . import opportunity_generation  # noqa: E402,F401
from . import content  # noqa: E402,F401
from . import platforms  # noqa: E402,F401
