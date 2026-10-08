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

# Generación de imágenes (Black Forest Labs / FLUX)
BFL_API_KEY = os.getenv("BFL_API_KEY", "")
BFL_MODEL = os.getenv("BFL_MODEL", "flux-pro-1.1")
BFL_BASE = os.getenv("BFL_BASE", "https://api.bfl.ai/v1")
IMAGE_WIDTH, IMAGE_HEIGHT = 1024, 1280  # 4:5, formato vertical de feed
MAX_IMAGES_PER_POST = 10

# Hosting público de imágenes (Instagram necesita una URL accesible): cloudinary | local
IMAGE_STORAGE = os.getenv("IMAGE_STORAGE", "local")
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "")
