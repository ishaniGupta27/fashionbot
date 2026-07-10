"""Main Fashionbot pipeline entrypoint.

Run with `python3 run_pipeline.py --id <id>`. The script validates
`code/input/<id>.json`, detects one of the internal modes from
`pipeline_config.py`, then normalizes inputs, generates VTO images, optionally
generates one video, and builds the final reel.
"""

import argparse
import os
import shlex
import subprocess

from pipeline_config import (
    BASE_DIR,
    MODE_4_BODY_TYPE_GARMENTS,
    MODE_2_BATCH_FOLDER,
    MODE_3_SINGLE_IMAGE_VIDEO,
    detect_mode,
    get_image_files,
    get_video_model,
    input_paths,
    load_config,
    mode_config,
    prompt_text,
)


def run(cmd):
    print("\n" + "=" * 80)
    print("RUNNING COMMAND")
    print(cmd)
    print("=" * 80)

    try:
        subprocess.run(
            cmd,
            shell=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        if "validate_input.py" in cmd:
            print("\nERROR: Validation failed. Fix the issue above and rerun.")
            raise SystemExit(e.returncode)

        print(f"\nERROR: Command failed with exit code {e.returncode}")
        print(cmd)
        raise SystemExit(e.returncode)


def quote(value):
    return shlex.quote(str(value))


def log_section(title):
    print("\n" + "-" * 80)
    print(title)
    print("-" * 80)


def log_kv(label, value):
    print(f"{label}: {value}")


def reel_duration(reel, key, default):
    return float(reel.get(key, default))


def clear_image_files(image_dir):
    if not os.path.isdir(image_dir):
        return

    for filename in get_image_files(image_dir):
        os.remove(os.path.join(image_dir, filename))


def first_model_name(path):
    return os.path.splitext(os.path.basename(path))[0]


def video_source_output_path(paths, video_model_path):
    """Dedicated VTO still used as the source image for video generation."""
    model_name = first_model_name(video_model_path)
    return os.path.join(
        paths["vto_output_dir"],
        f"video_source__{model_name}.jpg"
    )


def video_output_path(paths, video_model_path):
    model_name = first_model_name(video_model_path)
    return os.path.join(
        paths["video_output_dir"],
        f"video_source__{model_name}.mp4"
    )


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--id",
        required=True,
        help="Garment number (e.g. 6)"
    )

    args = parser.parse_args()
    garment_id = str(args.id)
    paths = input_paths(garment_id)

    print("\n🚀 FASHIONBOT PIPELINE")
    log_kv("Garment ID", garment_id)
    log_kv("Base dir", BASE_DIR)

    log_section("STEP 0/4")
    print("Validate input config")
    run(f"python3 validate_input.py --id {quote(garment_id)}")

    config = load_config(garment_id)
    archetypes = config["archetypes"]
    vto = config["vto"]
    video = config.get("video", {})
    reel = config.get("reel", {})
    original_image_description = (
        reel.get("original_image_description")
        or config.get("original_image_description")
    )
    original_image_credit = (
        reel.get("original_image_credit")
        or config.get("original_image_credit")
    )

    vto_model = vto.get("model", "fash")
    vto_prompt = prompt_text(vto.get("prompt"), "vto.prompt")
    append_garment_name_to_prompt = bool(
        vto.get("append_garment_name_to_prompt", False)
    )
    mode = detect_mode(garment_id, config)
    features = mode_config(mode)
    folder_mode = mode == MODE_2_BATCH_FOLDER
    body_type_mode = mode == MODE_4_BODY_TYPE_GARMENTS
    video_enabled = mode == MODE_3_SINGLE_IMAGE_VIDEO
    default_intro_duration = 2.1 if body_type_mode else 1.8
    default_result_duration = 1.5 if body_type_mode else 1.0
    default_end_card_duration = 1.5 if body_type_mode else 1.0
    intro_duration = reel_duration(
        reel,
        "intro_duration",
        default_intro_duration
    )
    result_duration = reel_duration(
        reel,
        "result_duration",
        default_result_duration
    )
    end_card_duration = reel_duration(
        reel,
        "end_card_duration",
        default_end_card_duration
    )

    log_section("CONFIG LOADED")
    log_kv("Execution mode", mode)
    log_kv("Mode description", features["description"])
    log_kv("Mode normalization", features["normalization"])
    log_kv("Mode VTO", features["vto"])
    log_kv("Mode reel", features["reel"])
    log_kv("Mode video", features["video"])
    log_kv("Intro features", features["intro_features"])
    log_kv("Voiceover", features["voiceover"])
    log_kv("Mascot", features["mascot"])
    log_kv("VTO model", vto_model)
    log_kv("VTO prompt present", bool(vto_prompt))
    log_kv("Append garment name to prompt", append_garment_name_to_prompt)
    log_kv("Video enabled", video_enabled)
    log_kv("Single garment candidate", paths["single_garment"])
    log_kv("Folder garment candidate", paths["garments_folder"])
    log_kv("Output image dir", paths["vto_output_dir"])
    log_kv("Output reel", paths["reel_output"])

    if folder_mode:
        garment_files = get_image_files(paths["garments_folder"])
        model_dir = archetypes[features["archetype_key"]]
        model_files = get_image_files(model_dir)

        print("Detected mode: MODE 2 - many garments to many models")
        log_kv("Input folder", paths["garments_folder"])
        log_kv("Normalized garments folder", paths["normalized_garments_folder"])
        log_kv("Model folder", model_dir)
        log_kv("Garments found", len(garment_files))
        log_kv("Models found", len(model_files))
        log_kv("Total VTO calls", len(garment_files) * len(model_files))
        log_kv("Garment files", ", ".join(garment_files))
        log_kv("Model files", ", ".join(model_files))

        reel_dress_image = os.path.join(
            paths["normalized_garments_folder"],
            garment_files[0]
        )
        reel_garments_dir = paths["normalized_garments_folder"]
    elif body_type_mode:
        garment_files = get_image_files(paths["garments_folder"])
        body_type_model = archetypes[features["archetype_key"]]

        print("Detected mode: MODE 4 - one body type to many garments")
        log_kv("Original body image", paths["single_garment"])
        log_kv("Normalized body image", paths["normalized_single_garment"])
        log_kv("Input garment folder", paths["garments_folder"])
        log_kv("Normalized garments folder", paths["normalized_garments_folder"])
        log_kv("Body/avatar model image", body_type_model)
        log_kv("Garments found", len(garment_files))
        log_kv("Total VTO calls", len(garment_files))
        log_kv("Garment files", ", ".join(garment_files))

        reel_dress_image = paths["normalized_single_garment"]
        reel_garments_dir = None
    elif video_enabled:
        video_model_path = archetypes["video_model"]

        print("Detected mode: MODE 3 - one garment to one video model")
        log_kv("Input image", paths["single_garment"])
        log_kv("Normalized image", paths["normalized_single_garment"])
        log_kv("Video model image", video_model_path)
        log_kv("Total VTO calls", 1)

        reel_dress_image = paths["normalized_single_garment"]
        reel_garments_dir = None
    else:
        model_dir = archetypes[features["archetype_key"]]
        model_files = get_image_files(model_dir)

        print("Detected mode: MODE 1 - one garment to many models")
        log_kv("Input image", paths["single_garment"])
        log_kv("Normalized image", paths["normalized_single_garment"])
        log_kv("Model folder", model_dir)
        log_kv("Models found", len(model_files))
        log_kv("Total VTO calls", len(model_files))
        log_kv("Model files", ", ".join(model_files))

        reel_dress_image = paths["normalized_single_garment"]
        reel_garments_dir = None

    log_section("STEP 1/4")

    if folder_mode or body_type_mode:
        if body_type_mode:
            print("Normalize original body/reference image")
            log_kv("Normalize input", paths["single_garment"])
            log_kv("Expected normalized output", paths["normalized_single_garment"])

            run(
                f"python3 normalize.py "
                f"--input {quote(paths['single_garment'])}"
            )

        print("Normalize all garment images")
        log_kv("Normalize input folder", paths["garments_folder"])
        log_kv("Normalized garments folder", paths["normalized_garments_folder"])

        os.makedirs(paths["normalized_garments_folder"], exist_ok=True)
        clear_image_files(paths["normalized_garments_folder"])

        for garment_file in garment_files:
            input_path = os.path.join(paths["garments_folder"], garment_file)
            output_path = os.path.join(
                paths["normalized_garments_folder"],
                garment_file
            )

            log_kv("Normalize garment", f"{input_path} -> {output_path}")

            run(
                f"python3 normalize.py "
                f"--input {quote(input_path)} "
                f"--output {quote(output_path)}"
            )
    else:
        print("Normalize garment")
        log_kv("Normalize input", paths["single_garment"])
        log_kv("Expected normalized output", paths["normalized_single_garment"])

        run(
            f"python3 normalize.py "
            f"--input {quote(paths['single_garment'])}"
        )

    log_section("STEP 2/4")
    print("Generate VTON images")
    log_kv("VTO output dir", paths["vto_output_dir"])

    if folder_mode:
        log_kv("generate_vto input mode", "--garments")
        log_kv("Garments dir", paths["normalized_garments_folder"])
        log_kv("Models dir", model_dir)

        run(
            f"python3 generate_vto.py "
            f"--garments {quote(paths['normalized_garments_folder'])} "
            f"--models {quote(model_dir)} "
            f"--output {quote(paths['vto_output_dir'])} "
            f"--model {quote(vto_model)}"
            + (f" --prompt {quote(vto_prompt)}" if vto_prompt else "")
            + (
                " --append-garment-name-to-prompt"
                if append_garment_name_to_prompt
                else ""
            )
        )
    elif body_type_mode:
        log_kv("generate_vto input mode", "--garments --model-image")
        log_kv("Garments dir", paths["normalized_garments_folder"])
        log_kv("Body/avatar model image", body_type_model)

        run(
            f"python3 generate_vto.py "
            f"--garments {quote(paths['normalized_garments_folder'])} "
            f"--model-image {quote(body_type_model)} "
            f"--output {quote(paths['vto_output_dir'])} "
            f"--model {quote(vto_model)}"
            + (f" --prompt {quote(vto_prompt)}" if vto_prompt else "")
            + (
                " --append-garment-name-to-prompt"
                if append_garment_name_to_prompt
                else ""
            )
        )
    elif video_enabled:
        print("Video mode uses only the dedicated video_model VTO still.")
        log_kv("generate_vto input mode", "--model-image")
        log_kv("Dress image", paths["normalized_single_garment"])
        log_kv("Video model image", archetypes["video_model"])
    else:
        log_kv("generate_vto input mode", "--dress")
        log_kv("Dress image", paths["normalized_single_garment"])
        log_kv("Models dir", model_dir)

        run(
            f"python3 generate_vto.py "
            f"--dress {quote(paths['normalized_single_garment'])} "
            f"--models {quote(model_dir)} "
            f"--output {quote(paths['vto_output_dir'])} "
            f"--model {quote(vto_model)}"
            + (f" --prompt {quote(vto_prompt)}" if vto_prompt else "")
            + (
                " --append-garment-name-to-prompt"
                if append_garment_name_to_prompt
                else ""
            )
        )

    reel_results_dir = paths["vto_output_dir"]

    log_section("STEP 3/4")

    if video_enabled:
        print("Generate one video from one dedicated VTO source image")
        video_model_path = archetypes["video_model"]
        video_source_image = video_source_output_path(paths, video_model_path)
        generated_video = video_output_path(paths, video_model_path)

        log_kv("Video model image", video_model_path)
        log_kv("Video source VTO image", video_source_image)
        log_kv("Video output", generated_video)

        run(
            f"python3 generate_vto.py "
            f"--dress {quote(paths['normalized_single_garment'])} "
            f"--model-image {quote(video_model_path)} "
            f"--output {quote(video_source_image)} "
            f"--model {quote(vto_model)}"
            + (f" --prompt {quote(vto_prompt)}" if vto_prompt else "")
            + (
                " --append-garment-name-to-prompt"
                if append_garment_name_to_prompt
                else ""
            )
        )

        video_model_id = get_video_model(config)
        video_prompt = prompt_text(video["prompt"], "video.prompt")

        video_cmd = (
            f"python3 generate_video.py "
            f"--source-image {quote(video_source_image)} "
            f"--output {quote(generated_video)} "
            f"--model {quote(video_model_id)} "
            f"--prompt {quote(video_prompt)} "
            f"--duration {quote(str(video.get('duration', '5')))}"
        )

        if video.get("generate_audio", False):
            video_cmd += " --generate-audio"

        if video.get("negative_prompt"):
            video_cmd += f" --negative-prompt {quote(video['negative_prompt'])}"

        if video.get("cfg_scale") is not None:
            video_cmd += f" --cfg-scale {quote(str(video['cfg_scale']))}"

        run(video_cmd)

        reel_featured_image = video_source_image
        reel_featured_video = generated_video
    else:
        print("Video disabled. Skipping video generation.")
        reel_featured_image = None
        reel_featured_video = None

    log_section("STEP 4/4")
    print("Build reel")
    log_kv("Reel intro image", reel_dress_image)
    log_kv("Reel results dir", reel_results_dir)
    log_kv("Reel featured image", reel_featured_image or "(none)")
    log_kv("Reel featured video", reel_featured_video or "(none)")
    log_kv("Reel intro features", features["intro_features"])
    log_kv("Reel intro duration", f"{intro_duration:g} sec")
    log_kv("Reel result duration", f"{result_duration:g} sec")
    log_kv("Reel end card duration", f"{end_card_duration:g} sec")
    log_kv("Body type intro layout", body_type_mode)
    log_kv("Result name labels", body_type_mode)
    log_kv("Original image description", original_image_description or "(none)")
    log_kv("Original image credit", original_image_credit or "(none)")
    log_kv("Reel output", paths["reel_output"])

    run(
        f"python3 build_reel_audio.py "
        f"--dress {quote(reel_dress_image)} "
        f"--results {quote(reel_results_dir)} "
        f"--output {quote(paths['reel_output'])}"
        + (f" --garments {quote(reel_garments_dir)}" if reel_garments_dir else "")
        + (" --intro-features" if features["intro_features"] else "")
        + (
            f" --featured-image {quote(reel_featured_image)}"
            if reel_featured_image
            else ""
        )
        + (
            f" --featured-video {quote(reel_featured_video)}"
            if reel_featured_video
            else ""
        )
        + (
            f" --original-image-description {quote(original_image_description)}"
            if original_image_description
            else ""
        )
        + (
            f" --original-image-credit {quote(original_image_credit)}"
            if original_image_credit
            else ""
        )
        + (" --body-type-intro" if body_type_mode else "")
        + (" --result-name-labels" if body_type_mode else "")
        + f" --intro-duration {quote(str(intro_duration))}"
        + f" --result-duration {quote(str(result_duration))}"
        + f" --end-card-duration {quote(str(end_card_duration))}"
    )

    print("\n🎉 DONE")
    print("\nFinal Reel:")
    print(paths["reel_output"])
