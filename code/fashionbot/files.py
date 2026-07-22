import os
from pathlib import Path

from .settings import AUDIO_EXTENSIONS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS


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

