import io
import os
from pathlib import Path

from PIL import Image, ImageStat

from .settings import AUDIO_EXTENSIONS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS


MIN_IMAGE_BYTES = 2048
MIN_IMAGE_DIMENSION = 64
MIN_ASPECT_RATIO = 0.3
MAX_ASPECT_RATIO = 3.0
NEAR_BLACK_MEAN = 10.0
NEAR_WHITE_MEAN = 245.0
FLAT_STDDEV = 3.0
DOMINANT_COLOR_RATIO = 0.95


def image_files(path):
    folder = Path(path)
    if not folder.is_dir():
        return []

    return sorted(
        item
        for item in folder.iterdir()
        if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS
    )


def media_files(path):
    folder = Path(path)
    if not folder.is_dir():
        return []

    return sorted(
        item
        for item in folder.iterdir()
        if item.is_file()
        and item.suffix.lower() in IMAGE_EXTENSIONS + VIDEO_EXTENSIONS
    )


def resolve_media_file(path, extensions):
    if not path:
        return None

    candidate = Path(path)
    if candidate.exists():
        return candidate

    if candidate.suffix:
        return None

    for extension in extensions:
        with_extension = candidate.with_suffix(extension)
        if with_extension.exists():
            return with_extension

    return None


def resolve_audio_file(path):
    return resolve_media_file(path, AUDIO_EXTENSIONS)


def resolve_image_file(path):
    return resolve_media_file(path, IMAGE_EXTENSIONS)


def ensure_clean_image_dir(path):
    folder = Path(path)
    folder.mkdir(parents=True, exist_ok=True)

    for item in image_files(folder):
        item.unlink()


def output_exists(path):
    candidate = Path(path)
    return candidate.is_file() and candidate.stat().st_size > 0


def check_image(source):
    """Run cheap Tier-1 sanity checks on an image.

    Accepts a filesystem path or raw image bytes. Returns a short reason string
    describing why the image is bad, or None when the image passes all checks.
    """
    if isinstance(source, (bytes, bytearray)):
        data = bytes(source)
        if not data:
            return "empty bytes"
        if len(data) < MIN_IMAGE_BYTES:
            return f"tiny file ({len(data)} bytes)"
        opener = lambda: Image.open(io.BytesIO(data))
    else:
        path = Path(source)
        if not path.is_file():
            return "missing file"
        size = path.stat().st_size
        if size == 0:
            return "empty file"
        if size < MIN_IMAGE_BYTES:
            return f"tiny file ({size} bytes)"
        opener = lambda: Image.open(path)

    try:
        with opener() as img:
            img.load()
            rgb = img.convert("RGB")
    except Exception as e:
        return f"corrupt/unreadable ({e})"

    width, height = rgb.size
    if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
        return f"tiny dimensions ({width}x{height})"

    aspect = width / height if height else 0
    if aspect < MIN_ASPECT_RATIO or aspect > MAX_ASPECT_RATIO:
        return f"degenerate aspect ratio ({aspect:.2f})"

    gray = rgb.convert("L")
    stat = ImageStat.Stat(gray)
    mean = stat.mean[0]
    stddev = stat.stddev[0]

    if mean < NEAR_BLACK_MEAN:
        return f"near-black (mean {mean:.1f})"
    if mean > NEAR_WHITE_MEAN:
        return f"near-white (mean {mean:.1f})"
    if stddev < FLAT_STDDEV:
        return f"flat/low-variance (stddev {stddev:.1f})"

    total_pixels = width * height
    colors = rgb.getcolors(maxcolors=total_pixels)
    if colors:
        dominant_count = max(count for count, _ in colors)
        if dominant_count / total_pixels > DOMINANT_COLOR_RATIO:
            ratio = dominant_count / total_pixels
            return f"single dominant color ({ratio:.0%})"

    return None


def is_bad_image(source):
    return check_image(source) is not None


def display_name(path_or_name):
    stem = Path(path_or_name).stem

    if stem.endswith(".normalized"):
        stem = stem[: -len(".normalized")]

    if stem.startswith("code_"):
        stem = stem[len("code_"):]

    return (
        stem.replace("__", " ")
        .replace("_", " ")
        .replace("-", " ")
        .replace(":", "/")
        .strip()
    )


def safe_stem(path_or_name):
    return Path(path_or_name).stem.replace(os.sep, "_")

