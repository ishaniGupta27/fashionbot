import os
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
CODE_DIR = PACKAGE_DIR.parent
BASE_DIR = CODE_DIR.parent

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")
VIDEO_EXTENSIONS = (".mp4", ".mov", ".m4v")
AUDIO_EXTENSIONS = (".mp3", ".wav", ".m4a", ".aac")

MODE_ONE_BODY_MULTIPLE_GARMENTS = "one_body_multiple_garments"
MODE_ONE_GARMENT_MULTIPLE_BODIES = "one_garment_multiple_bodies"
MODE_MULTIPLE_GARMENTS_MULTIPLE_BODIES = "multiple_garments_multiple_bodies"
MODE_VIDEO = "video"

VALID_MODES = (
    MODE_ONE_BODY_MULTIPLE_GARMENTS,
    MODE_ONE_GARMENT_MULTIPLE_BODIES,
    MODE_MULTIPLE_GARMENTS_MULTIPLE_BODIES,
    MODE_VIDEO,
)

DEFAULT_VTO_MODEL = "flux"
DEFAULT_VIDEO_MODEL = "fal-ai/kling-video/v3/standard/image-to-video"

DEFAULT_INTRO_DURATION = 1.8
DEFAULT_RESULT_DURATION = 1.0
DEFAULT_END_CARD_DURATION = 1.0

BODY_TYPE_INTRO_DURATION = 2.1
BODY_TYPE_RESULT_DURATION = 1.5
BODY_TYPE_END_CARD_DURATION = 1.5

ASSETS_DIR = BASE_DIR / "assets"
DEFAULT_AUDIO = ASSETS_DIR / "audio" / "Jazz.mp3"
DEFAULT_INTRO_VOICEOVER = ASSETS_DIR / "audio" / "voiceover_intro"
DEFAULT_MASCOT_IMAGE = ASSETS_DIR / "reel" / "mascot"
DEFAULT_END_CARD = ASSETS_DIR / "reel" / "end.jpg"
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920


def jobs_dir():
    return Path(os.environ.get("FASHIONBOT_JOBS_DIR", BASE_DIR / "jobs")).expanduser()


def archetypes_dir():
    return Path(
        os.environ.get("FASHIONBOT_ARCHETYPES_DIR", BASE_DIR / "archetypes")
    ).expanduser()
