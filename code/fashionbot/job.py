import json
from dataclasses import dataclass
from pathlib import Path

from .archetypes import resolve_archetype, resolve_archetypes
from .errors import FashionbotError
from .files import image_files
from .settings import (
    BODY_TYPE_END_CARD_DURATION,
    BODY_TYPE_INTRO_DURATION,
    BODY_TYPE_RESULT_DURATION,
    DEFAULT_END_CARD_DURATION,
    DEFAULT_INTRO_DURATION,
    DEFAULT_RESULT_DURATION,
    DEFAULT_VIDEO_MODEL,
    DEFAULT_VTO_MODEL,
    MODE_MULTIPLE_GARMENTS_MULTIPLE_BODIES,
    MODE_ONE_BODY_MULTIPLE_GARMENTS,
    MODE_ONE_GARMENT_MULTIPLE_BODIES,
    MODE_VIDEO,
    VALID_MODES,
)


@dataclass
class Job:
    job_id: str
    mode: str
    root: Path
    config: dict
    archetype_root: Path
    archetype_metadata_root: Path
    outputs_dir: Path
    logs_dir: Path
    status_path: Path


def load_job(job_id, jobs_root, archetype_root, archetype_metadata_root=None):
    job_root = Path(jobs_root) / str(job_id)
    config_path = job_root / "job.json"

    if not config_path.is_file():
        raise FashionbotError(f"Missing job config: {config_path}")

    try:
        with config_path.open("r") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise FashionbotError(f"Invalid job.json: {e}") from e

    if not isinstance(config, dict):
        raise FashionbotError("job.json must contain a JSON object")

    mode = config.get("mode")
    if mode not in VALID_MODES:
        valid_modes = ", ".join(VALID_MODES)
        raise FashionbotError(f"mode must be one of: {valid_modes}")

    job = Job(
        job_id=str(job_id),
        mode=mode,
        root=job_root,
        config=config,
        archetype_root=Path(archetype_root),
        archetype_metadata_root=(
            Path(archetype_metadata_root)
            if archetype_metadata_root is not None
            else Path(archetype_root)
        ),
        outputs_dir=job_root / "outputs",
        logs_dir=job_root / "logs",
        status_path=job_root / "status.json",
    )

    validate_job(job)
    return job


def relpath(job, value, label):
    if not isinstance(value, str) or not value.strip():
        raise FashionbotError(f"{label} must be a non-empty relative path")

    path = Path(value)
    if path.is_absolute():
        raise FashionbotError(f"{label} must be relative to the job folder: {value}")

    return job.root / path


def require_section(config, section):
    value = config.get(section)
    if not isinstance(value, dict):
        raise FashionbotError(f"Missing required section: {section}")
    return value


def require_file(path, label):
    if not Path(path).is_file():
        raise FashionbotError(f"{label} must be a file: {path}")


def require_dir(path, label):
    if not Path(path).is_dir():
        raise FashionbotError(f"{label} must be a directory: {path}")


def require_images(path, label):
    files = image_files(path)
    if not files:
        raise FashionbotError(f"{label} must contain at least 1 image: {path}")
    return files


def prompt_text(value, label):
    if value is None:
        return None

    if isinstance(value, str):
        return value

    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return " ".join(item.strip() for item in value if item.strip())

    raise FashionbotError(f"{label} must be a string or a list of strings")


def positive_duration(value, label):
    if isinstance(value, bool):
        raise FashionbotError(f"{label} must be a positive number")

    try:
        duration = float(value)
    except (TypeError, ValueError) as e:
        raise FashionbotError(f"{label} must be a positive number") from e

    if duration <= 0:
        raise FashionbotError(f"{label} must be greater than 0")

    return duration


def reel_duration(job, key):
    defaults = {
        "intro_duration": (
            BODY_TYPE_INTRO_DURATION
            if job.mode == MODE_ONE_BODY_MULTIPLE_GARMENTS
            else DEFAULT_INTRO_DURATION
        ),
        "result_duration": (
            BODY_TYPE_RESULT_DURATION
            if job.mode == MODE_ONE_BODY_MULTIPLE_GARMENTS
            else DEFAULT_RESULT_DURATION
        ),
        "end_card_duration": (
            BODY_TYPE_END_CARD_DURATION
            if job.mode == MODE_ONE_BODY_MULTIPLE_GARMENTS
            else DEFAULT_END_CARD_DURATION
        ),
    }
    reel = job.config.get("reel", {})
    return positive_duration(reel.get(key, defaults[key]), f"reel.{key}")


def validate_models(job, models):
    if job.mode in (
        MODE_ONE_BODY_MULTIPLE_GARMENTS,
        MODE_VIDEO,
    ):
        archetype_id = models.get("archetype_id")
        if archetype_id is None:
            raise FashionbotError(f"{job.mode} requires models.archetype_id")
        resolve_archetype(
            archetype_id,
            job.archetype_root,
            job.archetype_metadata_root,
        )
        return

    archetype_ids = models.get("archetype_ids")
    if not isinstance(archetype_ids, list) or not archetype_ids:
        raise FashionbotError(f"{job.mode} requires models.archetype_ids")
    resolve_archetypes(
        archetype_ids,
        job.archetype_root,
        job.archetype_metadata_root,
    )


def validate_job(job):
    inputs = require_section(job.config, "inputs")
    models = require_section(job.config, "models")
    vto = require_section(job.config, "vto")
    reel = job.config.get("reel", {})

    if not isinstance(reel, dict):
        raise FashionbotError("reel must be an object when provided")

    validate_models(job, models)
    prompt_text(vto.get("prompt"), "vto.prompt")

    if vto.get("model", DEFAULT_VTO_MODEL) not in ("fash", "flux"):
        raise FashionbotError("vto.model must be 'fash' or 'flux'")

    if "append_garment_name_to_prompt" in vto and not isinstance(
        vto["append_garment_name_to_prompt"], bool
    ):
        raise FashionbotError("vto.append_garment_name_to_prompt must be true or false")

    for key in ("intro_duration", "result_duration", "end_card_duration"):
        reel_duration(job, key)

    if job.mode in (
        MODE_ONE_GARMENT_MULTIPLE_BODIES,
        MODE_VIDEO,
    ):
        garment = relpath(job, inputs.get("garment_image"), "inputs.garment_image")
        require_file(garment, "inputs.garment_image")

    if job.mode == MODE_MULTIPLE_GARMENTS_MULTIPLE_BODIES:
        garments_dir = relpath(job, inputs.get("garments_dir"), "inputs.garments_dir")
        require_dir(garments_dir, "inputs.garments_dir")
        require_images(garments_dir, "inputs.garments_dir")

    if job.mode == MODE_ONE_BODY_MULTIPLE_GARMENTS:
        original = relpath(job, inputs.get("original_image"), "inputs.original_image")
        garments_dir = relpath(job, inputs.get("garments_dir"), "inputs.garments_dir")
        require_file(original, "inputs.original_image")
        require_dir(garments_dir, "inputs.garments_dir")
        require_images(garments_dir, "inputs.garments_dir")

    if job.mode == MODE_VIDEO:
        video = require_section(job.config, "video")
        if prompt_text(video.get("prompt"), "video.prompt") is None:
            raise FashionbotError("video mode requires video.prompt")
        if "duration" in video and str(video["duration"]) not in [str(n) for n in range(3, 16)]:
            raise FashionbotError("video.duration must be a string or number from 3 to 15")
        video.get("model", DEFAULT_VIDEO_MODEL)
