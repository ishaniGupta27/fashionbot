"""Shared paths, file helpers, and internal execution modes for Fashionbot.

The user-facing pipeline stays simple: `python3 run_pipeline.py --id 33`.
This module centralizes how that id maps to files and which internal mode runs.
"""

import json
import os


BASE_DIR = "/Users/Himanshu/Documents/fashionbot"
CODE_DIR = f"{BASE_DIR}/code"
INPUT_DIR = f"{CODE_DIR}/input"
OG_DIR = f"{BASE_DIR}/garments/og"
GARMENTS_DIR = f"{BASE_DIR}/garments"
REELS_DIR = f"{BASE_DIR}/reels"

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")
VIDEO_EXTENSIONS = (".mp4", ".mov", ".m4v")
AUDIO_EXTENSIONS = (".mp3", ".wav", ".m4a", ".aac")

DEFAULT_VIDEO_MODEL = "fal-ai/kling-video/v3/standard/image-to-video"
DEFAULT_INTRO_VOICEOVER = f"{BASE_DIR}/Audio/voiceover_intro"
DEFAULT_MASCOT_IMAGE = f"{BASE_DIR}/garments/extras/mascot"

MODE_1_SINGLE_IMAGE = "mode_1_single_image"
MODE_2_BATCH_FOLDER = "mode_2_batch_folder"
MODE_3_SINGLE_IMAGE_VIDEO = "mode_3_single_image_video"
MODE_4_BODY_TYPE_GARMENTS = "mode_4_body_type_garments"
BODY_TYPE_GARMENTS_CONFIG_MODE = "body_type_garments"

PIPELINE_MODES = {
    # Mode 1: the classic flow. One normalized garment image is tried on many
    # archetype/model images, then those generated images become the reel.
    MODE_1_SINGLE_IMAGE: {
        "description": "single garment image to many VTO images",
        "archetype_key": "single_garment_models",
        "normalization": "single_image",
        "vto": "many_models",
        "video": False,
        "reel": "flat_images",
        "intro_features": False,
        "voiceover": False,
        "mascot": True
    },
    # Mode 2: batch garment workflow. This intentionally keeps presentation
    # features minimal because it is mostly for catalog-style comparison.
    MODE_2_BATCH_FOLDER: {
        "description": "many garment images to many VTO images",
        "archetype_key": "garment_batch_models",
        "normalization": "folder_images",
        "vto": "many_garments_many_models",
        "video": False,
        "reel": "grouped_images",
        "intro_features": False,
        "voiceover": False,
        "mascot": False
    },
    # Mode 3: single garment plus a costly video lane. It generates only one
    # dedicated VTO image from video_model, then makes one Kling video.
    MODE_3_SINGLE_IMAGE_VIDEO: {
        "description": "single garment image to one VTO image and video",
        "archetype_key": None,
        "video_archetype_key": "video_model",
        "normalization": "single_image",
        "vto": "video_model_only",
        "video": True,
        "reel": "featured_video",
        "intro_features": False,
        "voiceover": False,
        "mascot": True
    },
    # Mode 4: body/reference workflow. The single image is an original body
    # reference for the reel intro, while the folder contains garments to place
    # onto one similar body/avatar model image.
    MODE_4_BODY_TYPE_GARMENTS: {
        "description": "one body type image to many garment VTO images",
        "archetype_key": "body_type_model",
        "normalization": "folder_images",
        "vto": "many_garments_one_model",
        "video": False,
        "reel": "body_type_flat_images",
        "intro_features": False,
        "voiceover": False,
        "mascot": False
    }
}


def config_path_for_id(garment_id):
    return f"{INPUT_DIR}/{garment_id}.json"


def load_config(garment_id):
    config_path = config_path_for_id(garment_id)

    with open(config_path, "r") as f:
        return json.load(f)


def prompt_text(value, label="prompt"):
    if value is None:
        return None

    if isinstance(value, str):
        return value

    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return " ".join(item.strip() for item in value if item.strip())

    raise RuntimeError(f"{label} must be a string or a list of strings")


def get_image_files(image_dir):
    return sorted([
        f for f in os.listdir(image_dir)
        if (
            os.path.isfile(os.path.join(image_dir, f))
            and f.lower().endswith(IMAGE_EXTENSIONS)
        )
    ])


def get_media_files(media_dir):
    return sorted([
        f for f in os.listdir(media_dir)
        if (
            os.path.isfile(os.path.join(media_dir, f))
            and f.lower().endswith(IMAGE_EXTENSIONS + VIDEO_EXTENSIONS)
        )
    ])


def resolve_audio_file(path):
    if not path:
        return None

    if os.path.exists(path):
        return path

    _, ext = os.path.splitext(path)

    if ext:
        return None

    for audio_ext in AUDIO_EXTENSIONS:
        candidate = path + audio_ext

        if os.path.exists(candidate):
            return candidate

    return None


def resolve_image_file(path):
    if not path:
        return None

    if os.path.exists(path):
        return path

    _, ext = os.path.splitext(path)

    if ext:
        return None

    for image_ext in IMAGE_EXTENSIONS:
        candidate = path + image_ext

        if os.path.exists(candidate):
            return candidate

    return None


def input_paths(garment_id):
    return {
        "single_garment": f"{OG_DIR}/{garment_id}.jpg",
        "garments_folder": f"{OG_DIR}/{garment_id}",
        "normalized_single_garment": f"{OG_DIR}/{garment_id}.normalized.jpg",
        "vto_output_dir": f"{GARMENTS_DIR}/{garment_id}",
        "normalized_garments_folder": (
            f"{OG_DIR}/{garment_id}/_normalized_garments"
        ),
        "video_output_dir": f"{GARMENTS_DIR}/{garment_id}/videos",
        "reel_output": f"{REELS_DIR}/reel_{garment_id}.mp4"
    }


def is_video_enabled(config):
    return bool(config.get("video", {}).get("enabled", False))


def is_body_type_garments_mode(config):
    return config.get("mode") == BODY_TYPE_GARMENTS_CONFIG_MODE


def get_video_model(config):
    return config.get("video", {}).get("model") or DEFAULT_VIDEO_MODEL


def detect_mode(garment_id, config):
    """Return the internal execution mode for a run id and config."""
    paths = input_paths(garment_id)
    single_exists = os.path.isfile(paths["single_garment"])
    folder_exists = os.path.isdir(paths["garments_folder"])
    video_enabled = is_video_enabled(config)
    body_type_mode = is_body_type_garments_mode(config)

    if body_type_mode:
        if video_enabled:
            raise RuntimeError("body_type_garments mode does not support video.")

        if not single_exists:
            raise RuntimeError(
                "body_type_garments mode requires original body image: "
                f"{paths['single_garment']}"
            )

        if not folder_exists:
            raise RuntimeError(
                "body_type_garments mode requires garment folder: "
                f"{paths['garments_folder']}"
            )

        return MODE_4_BODY_TYPE_GARMENTS

    if single_exists and folder_exists:
        raise RuntimeError("Both single garment and garment folder exist.")

    if not single_exists and not folder_exists:
        raise RuntimeError("No garment input found for this id.")

    if folder_exists and video_enabled:
        raise RuntimeError(
            "Video generation requires single-garment mode. "
            f"Found folder input: {paths['garments_folder']}"
        )

    if folder_exists:
        return MODE_2_BATCH_FOLDER

    if video_enabled:
        return MODE_3_SINGLE_IMAGE_VIDEO

    return MODE_1_SINGLE_IMAGE


def mode_config(mode):
    return PIPELINE_MODES[mode]
