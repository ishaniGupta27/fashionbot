"""Chatty preflight validation for a Fashionbot run config.

This script intentionally runs before any expensive fal.ai calls. It checks the
input shape, JSON config, model paths, prompts, mode guardrails, and cost count.
"""

import argparse
import json
import os

from pipeline_config import (
    BASE_DIR,
    DEFAULT_INTRO_VOICEOVER,
    DEFAULT_MASCOT_IMAGE,
    MODE_4_BODY_TYPE_GARMENTS,
    MODE_2_BATCH_FOLDER,
    MODE_3_SINGLE_IMAGE_VIDEO,
    config_path_for_id,
    detect_mode,
    get_image_files,
    get_video_model,
    input_paths,
    is_video_enabled,
    load_config,
    mode_config,
    resolve_audio_file,
    resolve_image_file,
)


VALID_VTO_MODELS = ("fash", "flux")
VALID_VIDEO_DURATIONS = tuple(str(n) for n in range(3, 16))
OUTPUT_EXTENSION = ".jpg"


def log_section(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def log_kv(label, value):
    print(f"{label}: {value}")


def ok(message):
    print(f"OK: {message}")


def fail(message):
    raise RuntimeError(message)


def require_section(config, section):
    if section not in config or not isinstance(config[section], dict):
        fail(f"Missing required section: {section}")

    ok(f"Found section: {section}")


def require_path(label, path, expect_dir=False, expect_file=False):
    log_kv(label, path)

    if expect_dir and not os.path.isdir(path):
        fail(f"{label} must be a directory: {path}")

    if expect_file and not os.path.isfile(path):
        fail(f"{label} must be a file: {path}")

    ok(f"{label} exists")


def output_exists(path):
    return os.path.isfile(path) and os.path.getsize(path) > 0


def first_model_name(path):
    return os.path.splitext(os.path.basename(path))[0]


def count_existing_vto_outputs(
    mode,
    paths,
    garment_files,
    model_files,
    archetypes
):
    existing = 0

    if mode == MODE_3_SINGLE_IMAGE_VIDEO:
        video_model = archetypes.get("video_model")

        if video_model:
            video_source_path = os.path.join(
                paths["vto_output_dir"],
                f"video_source__{first_model_name(video_model)}.jpg"
            )

            if output_exists(video_source_path):
                existing += 1

        return existing

    if mode == MODE_4_BODY_TYPE_GARMENTS:
        for garment_file in garment_files:
            output_path = os.path.join(
                paths["vto_output_dir"],
                os.path.splitext(garment_file)[0] + OUTPUT_EXTENSION
            )

            if output_exists(output_path):
                existing += 1

        return existing

    if mode == MODE_2_BATCH_FOLDER:
        for garment_file in garment_files:
            garment_name = os.path.splitext(garment_file)[0]

            for model_file in model_files:
                model_name = os.path.splitext(model_file)[0]
                output_path = os.path.join(
                    paths["vto_output_dir"],
                    f"{garment_name}__{model_name}{OUTPUT_EXTENSION}"
                )

                if output_exists(output_path):
                    existing += 1

        return existing

    for model_file in model_files:
        output_path = os.path.join(
            paths["vto_output_dir"],
            os.path.splitext(model_file)[0] + OUTPUT_EXTENSION
        )

        if output_exists(output_path):
            existing += 1

    return existing


def count_video_outputs(mode, paths, archetypes):
    if mode != MODE_3_SINGLE_IMAGE_VIDEO:
        return 0

    video_model = archetypes.get("video_model")

    if not video_model:
        return 0

    video_path = os.path.join(
        paths["video_output_dir"],
        f"video_source__{first_model_name(video_model)}.mp4"
    )

    return 1 if output_exists(video_path) else 0


def validate(garment_id):
    paths = input_paths(garment_id)
    config_path = config_path_for_id(garment_id)

    log_section("VALIDATING INPUT CONFIG")
    log_kv("Base dir", BASE_DIR)
    log_kv("Config file", config_path)

    if not os.path.isfile(config_path):
        fail(f"Missing config file: {config_path}")

    try:
        config = load_config(garment_id)
    except json.JSONDecodeError as e:
        fail(f"Invalid JSON: {e}")

    ok("Config JSON parsed")

    require_section(config, "archetypes")
    require_section(config, "vto")

    archetypes = config["archetypes"]
    vto = config["vto"]
    video = config.get("video", {})
    reel = config.get("reel", {})

    log_section("INPUT MODE")
    single_exists = os.path.isfile(paths["single_garment"])
    folder_exists = os.path.isdir(paths["garments_folder"])

    log_kv("Single garment candidate", paths["single_garment"])
    log_kv("Single garment exists", single_exists)
    log_kv("Folder garment candidate", paths["garments_folder"])
    log_kv("Folder exists", folder_exists)

    try:
        mode = detect_mode(garment_id, config)
    except RuntimeError as e:
        fail(str(e))

    features = mode_config(mode)
    folder_mode = mode == MODE_2_BATCH_FOLDER
    body_type_mode = mode == MODE_4_BODY_TYPE_GARMENTS

    ok(f"Detected execution mode: {mode}")
    log_kv("Mode description", features["description"])
    log_kv("Mode normalization", features["normalization"])
    log_kv("Mode VTO", features["vto"])
    log_kv("Mode reel", features["reel"])
    log_kv("Mode video", features["video"])
    log_kv("Intro features", features["intro_features"])
    log_kv("Voiceover", features["voiceover"])
    log_kv("Mascot", features["mascot"])

    log_section("ARCHETYPES")
    video_model = archetypes.get("video_model")

    active_archetype_key = features["archetype_key"]
    active_model_files = []

    if mode == MODE_3_SINGLE_IMAGE_VIDEO:
        require_path("video_model", video_model, expect_file=True)
        ok("Mode 3 skips single_garment_models")
    elif body_type_mode:
        body_type_model = archetypes.get(active_archetype_key)
        require_path(active_archetype_key, body_type_model, expect_file=True)
        active_model_files = [os.path.basename(body_type_model)]
        ok("Body type model image configured")
    else:
        active_model_dir = archetypes.get(active_archetype_key)

        require_path(active_archetype_key, active_model_dir, expect_dir=True)
        active_model_files = get_image_files(active_model_dir)

        if not active_model_files:
            fail(f"{active_archetype_key} has no image files")

        ok(f"Active model image count: {len(active_model_files)}")

    log_section("VTO")
    vto_model = vto.get("model", "fash")
    vto_prompt = vto.get("prompt")
    log_kv("VTO model", vto_model)
    log_kv("VTO prompt present", bool(vto_prompt))

    if vto_model not in VALID_VTO_MODELS:
        fail(f"Invalid VTO model: {vto_model}")

    if vto_model == "flux" and not vto_prompt:
        fail("vto.prompt is required when vto.model is flux")

    ok("VTO config looks good")

    log_section("REEL")
    original_image_description = (
        reel.get("original_image_description")
        or config.get("original_image_description")
    )
    original_image_credit = (
        reel.get("original_image_credit")
        or config.get("original_image_credit")
    )
    log_kv("Original image description", original_image_description or "(none)")
    log_kv("Original image credit", original_image_credit or "(none)")

    if (
        original_image_description is not None
        and not isinstance(original_image_description, str)
    ):
        fail("reel.original_image_description must be a string when provided")

    if original_image_credit is not None and not isinstance(original_image_credit, str):
        fail("reel.original_image_credit must be a string when provided")

    ok("Reel config looks good")

    log_section("VIDEO")
    video_enabled = is_video_enabled(config)
    log_kv("Video enabled", video_enabled)

    if video_enabled:
        video_prompt = video.get("prompt")
        video_duration = str(video.get("duration", "5"))
        video_model_id = get_video_model(config)

        log_kv("Video model", video_model_id)
        log_kv("Video prompt present", bool(video_prompt))
        log_kv("Video duration", video_duration)
        log_kv("Video output dir", paths["video_output_dir"])

        if not video_prompt:
            fail("video.prompt is required when video.enabled is true")

        if video_duration not in VALID_VIDEO_DURATIONS:
            fail(f"video.duration must be 3-15 seconds: {video_duration}")

        ok("Video config looks good")
    else:
        ok("Video disabled")

    log_section("INTRO AUDIO")

    if features["voiceover"]:
        intro_voiceover = resolve_audio_file(DEFAULT_INTRO_VOICEOVER)
        log_kv("Voiceover expected for mode", True)
        log_kv("Voiceover lookup", DEFAULT_INTRO_VOICEOVER)

        if intro_voiceover:
            log_kv("Voiceover file", intro_voiceover)
            ok("Intro voiceover will be used")
        else:
            ok("Intro voiceover not found; reel will continue without it")
    else:
        log_kv("Voiceover expected for mode", False)
        ok("Voiceover not used for this mode")

    log_section("INTRO MASCOT")

    if features["mascot"]:
        mascot_image = resolve_image_file(DEFAULT_MASCOT_IMAGE)
        log_kv("Mascot expected for mode", True)
        log_kv("Mascot lookup", DEFAULT_MASCOT_IMAGE)

        if mascot_image:
            log_kv("Mascot file", mascot_image)
            ok("Intro mascot will be used")
        else:
            ok("Intro mascot not found; reel will continue without it")
    else:
        log_kv("Mascot expected for mode", False)
        ok("Mascot not used for this mode")

    log_section("COST PREVIEW")

    if folder_mode or body_type_mode:
        garment_files = get_image_files(paths["garments_folder"])
    else:
        garment_files = [os.path.basename(paths["single_garment"])]

    if mode == MODE_3_SINGLE_IMAGE_VIDEO:
        model_files = [os.path.basename(video_model)]
        total_vto_pairs = 1
    elif body_type_mode:
        model_files = active_model_files
        total_vto_pairs = len(garment_files)
    else:
        model_files = active_model_files
        total_vto_pairs = len(garment_files) * len(model_files)

    existing_vto_outputs = count_existing_vto_outputs(
        mode,
        paths,
        garment_files,
        model_files,
        archetypes
    )
    existing_video_outputs = count_video_outputs(mode, paths, archetypes)
    total_video_calls = 1 if video_enabled else 0

    log_kv("Garments found", len(garment_files))
    log_kv("Models found", len(model_files))
    log_kv("VTO outputs already present", existing_vto_outputs)
    log_kv("VTO calls needing generation", max(total_vto_pairs - existing_vto_outputs, 0))
    log_kv("Video outputs already present", existing_video_outputs)
    log_kv("Video calls needing generation", max(total_video_calls - existing_video_outputs, 0))

    log_section("VALIDATION PASSED")
    ok("Input is ready for pipeline")

    return config


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)

    args = parser.parse_args()

    validate(str(args.id))
