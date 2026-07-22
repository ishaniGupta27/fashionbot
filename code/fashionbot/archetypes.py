import json
from pathlib import Path

from .errors import FashionbotError
from .settings import IMAGE_EXTENSIONS


def load_catalog(root):
    catalog_path = Path(root) / "catalog.json"

    if not catalog_path.is_file():
        return {}

    try:
        with catalog_path.open("r") as f:
            catalog = json.load(f)
    except json.JSONDecodeError as e:
        raise FashionbotError(f"Invalid archetype catalog JSON: {e}") from e

    if not isinstance(catalog, dict):
        raise FashionbotError("archetypes/catalog.json must be a JSON object")

    return catalog


def resolve_archetype(archetype_id, root):
    archetype_id = str(archetype_id)
    root = Path(root)
    catalog = load_catalog(root)

    if archetype_id in catalog:
        path = root / catalog[archetype_id]
        if not path.is_file():
            raise FashionbotError(
                f"Archetype {archetype_id} points to missing file: {path}"
            )
        return path

    direct_matches = [
        root / f"{archetype_id}{extension}" for extension in IMAGE_EXTENSIONS
    ]
    for candidate in direct_matches:
        if candidate.is_file():
            return candidate

    recursive_matches = sorted(
        item
        for item in root.rglob("*")
        if item.is_file()
        and item.suffix.lower() in IMAGE_EXTENSIONS
        and item.stem == archetype_id
    )

    if not recursive_matches:
        raise FashionbotError(
            f"Unknown archetype id '{archetype_id}'. Add it to {root / 'catalog.json'} "
            "or place an image with that id in the archetype folder."
        )

    if len(recursive_matches) > 1:
        matches = "\n".join(f"- {path}" for path in recursive_matches[:10])
        raise FashionbotError(
            f"Archetype id '{archetype_id}' is ambiguous. Add it to "
            f"{root / 'catalog.json'}.\n{matches}"
        )

    return recursive_matches[0]


def resolve_archetypes(archetype_ids, root):
    return [resolve_archetype(archetype_id, root) for archetype_id in archetype_ids]

