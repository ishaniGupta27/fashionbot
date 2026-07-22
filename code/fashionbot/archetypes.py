import json
from pathlib import Path

from .errors import FashionbotError
from .settings import IMAGE_EXTENSIONS


def load_catalog(metadata_root):
    catalog_path = Path(metadata_root) / "catalog.json"

    if not catalog_path.is_file():
        return {}

    try:
        with catalog_path.open("r") as f:
            catalog = json.load(f)
    except json.JSONDecodeError as e:
        raise FashionbotError(f"Invalid archetype catalog JSON: {e}") from e

    if not isinstance(catalog, dict):
        raise FashionbotError("archetype_metadata/catalog.json must be a JSON object")

    return catalog


def resolve_archetype(archetype_id, image_root, metadata_root=None):
    archetype_id = str(archetype_id)
    image_root = Path(image_root)
    metadata_root = Path(metadata_root) if metadata_root is not None else image_root
    catalog_path = metadata_root / "catalog.json"
    catalog = load_catalog(metadata_root)

    if archetype_id in catalog:
        path = image_root / catalog[archetype_id]
        if not path.is_file():
            raise FashionbotError(
                f"Archetype {archetype_id} points to missing file: {path}"
            )
        return path

    direct_matches = [
        image_root / f"{archetype_id}{extension}" for extension in IMAGE_EXTENSIONS
    ]
    for candidate in direct_matches:
        if candidate.is_file():
            return candidate

    recursive_matches = sorted(
        item
        for item in image_root.rglob("*")
        if item.is_file()
        and item.suffix.lower() in IMAGE_EXTENSIONS
        and item.stem == archetype_id
    )

    if not recursive_matches:
        raise FashionbotError(
            f"Unknown archetype id '{archetype_id}'. Add it to {catalog_path} "
            "or place an image with that id in the archetype image folder."
        )

    if len(recursive_matches) > 1:
        matches = "\n".join(f"- {path}" for path in recursive_matches[:10])
        raise FashionbotError(
            f"Archetype id '{archetype_id}' is ambiguous. Add it to "
            f"{catalog_path}.\n{matches}"
        )

    return recursive_matches[0]


def resolve_archetypes(archetype_ids, image_root, metadata_root=None):
    return [
        resolve_archetype(archetype_id, image_root, metadata_root)
        for archetype_id in archetype_ids
    ]
