import os


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "si", "sí")


MODEL = os.getenv("SWARM_MODEL", "claude-sonnet-5-5")
DRY_RUN = _bool("DRY_RUN", True)
REQUIRE_APPROVAL = _bool("REQUIRE_APPROVAL", True)
IG_USER_ID = os.getenv("IG_USER_ID", "")
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN", "")
GRAPH_VERSION = os.getenv("GRAPH_VERSION", "v21.0")
MAX_POSTS_PER_DAY = int(os.getenv("MAX_POSTS_PER_DAY", "2"))
DB_PATH = os.getenv("SWARM_DB", "data/queue.db")
MAX_REVISIONS = 2
