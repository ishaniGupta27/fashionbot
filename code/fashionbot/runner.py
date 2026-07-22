from pathlib import Path

from .archetypes import resolve_archetype, resolve_archetypes
from .dry_run import (
    mock_video,
    mock_vto_for_garments,
    mock_vto_for_models,
    mock_vto_grid,
)
from .errors import FashionbotError
from .files import ensure_clean_image_dir, image_files
from .job import prompt_text, reel_duration, relpath
from .normalize import normalize_image
from .reel import build_reel
from .settings import (
    DEFAULT_VIDEO_MODEL,
    DEFAULT_VTO_MODEL,
    MODE_MULTIPLE_GARMENTS_MULTIPLE_BODIES,
    MODE_ONE_BODY_MULTIPLE_GARMENTS,
    MODE_ONE_GARMENT_MULTIPLE_BODIES,
    MODE_VIDEO,
)
from .status import write_status
from .video import generate_video
from .vto import (
    many_garments_to_many_bodies,
    many_garments_to_one_body,
    one_garment_to_many_bodies,
    one_garment_to_one_body,
)


def log_section(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def log_kv(label, value):
    print(f"{label}: {value}")


def vto_settings(job):
    vto = job.config["vto"]
    return {
        "model": vto.get("model", DEFAULT_VTO_MODEL),
        "prompt": prompt_text(vto.get("prompt"), "vto.prompt"),
        "append_garment_name": bool(vto.get("append_garment_name_to_prompt", False)),
    }


def reel_settings(job):
    reel = job.config.get("reel", {})
    return {
        "original_image_description": reel.get("original_image_description"),
        "original_image_credit": reel.get("original_image_credit"),
        "intro_duration": reel_duration(job, "intro_duration"),
        "result_duration": reel_duration(job, "result_duration"),
        "end_card_duration": reel_duration(job, "end_card_duration"),
        "show_result_name_labels": bool(reel.get("show_result_name_labels", False)),
    }


def normalized_single_path(job, name):
    return job.outputs_dir / "normalized" / name


def normalized_garments_dir(job):
    return job.outputs_dir / "normalized" / "garments"


def normalize_garment_file(job, garment_path):
    output_path = normalized_single_path(job, Path(garment_path).name)
    print(f"Normalize: {garment_path} -> {output_path}")
    return normalize_image(garment_path, output_path)


def normalize_garment_folder(job, garments_dir):
    output_dir = normalized_garments_dir(job)
    ensure_clean_image_dir(output_dir)

    for garment_path in image_files(garments_dir):
        output_path = output_dir / garment_path.name
        print(f"Normalize: {garment_path} -> {output_path}")
        normalize_image(garment_path, output_path)

    return output_dir


def mode_one_garment_multiple_bodies(job, dry_run=False):
    inputs = job.config["inputs"]
    models = job.config["models"]
    vto = vto_settings(job)
    reel = reel_settings(job)

    garment = relpath(job, inputs["garment_image"], "inputs.garment_image")
    model_paths = resolve_archetypes(models["archetype_ids"], job.archetype_root)
    normalized_garment = normalize_garment_file(job, garment)
    vto_dir = job.outputs_dir / "vto"
    vto_dir.mkdir(parents=True, exist_ok=True)

    if dry_run:
        mock_vto_for_models(normalized_garment, model_paths, vto_dir)
        skipped = []
    else:
        skipped = one_garment_to_many_bodies(
            normalized_garment,
            model_paths,
            vto_dir,
            model=vto["model"],
            prompt=vto["prompt"],
            append_garment_name=vto["append_garment_name"],
        )

    reel_path = job.outputs_dir / "reel.mp4"
    build_reel(
        normalized_garment,
        vto_dir,
        reel_path,
        original_image_description=reel["original_image_description"],
        original_image_credit=reel["original_image_credit"],
        intro_duration=reel["intro_duration"],
        result_duration=reel["result_duration"],
        end_card_duration=reel["end_card_duration"],
    )
    return {"reel": str(reel_path), "vto_dir": str(vto_dir), "skipped_vto": skipped}


def mode_multiple_garments_multiple_bodies(job, dry_run=False):
    inputs = job.config["inputs"]
    models = job.config["models"]
    vto = vto_settings(job)
    reel = reel_settings(job)

    garments_dir = relpath(job, inputs["garments_dir"], "inputs.garments_dir")
    model_paths = resolve_archetypes(models["archetype_ids"], job.archetype_root)
    normalized_dir = normalize_garment_folder(job, garments_dir)
    vto_dir = job.outputs_dir / "vto"
    vto_dir.mkdir(parents=True, exist_ok=True)

    if dry_run:
        mock_vto_grid(normalized_dir, model_paths, vto_dir)
        skipped = []
    else:
        skipped = many_garments_to_many_bodies(
            normalized_dir,
            model_paths,
            vto_dir,
            model=vto["model"],
            prompt=vto["prompt"],
            append_garment_name=vto["append_garment_name"],
        )

    reel_path = job.outputs_dir / "reel.mp4"
    build_reel(
        next(iter(image_files(normalized_dir))),
        vto_dir,
        reel_path,
        garments_dir=normalized_dir,
        original_image_description=reel["original_image_description"],
        original_image_credit=reel["original_image_credit"],
        result_duration=reel["result_duration"],
        end_card_duration=reel["end_card_duration"],
    )
    return {"reel": str(reel_path), "vto_dir": str(vto_dir), "skipped_vto": skipped}


def mode_one_body_multiple_garments(job, dry_run=False):
    inputs = job.config["inputs"]
    models = job.config["models"]
    vto = vto_settings(job)
    reel = reel_settings(job)

    original = relpath(job, inputs["original_image"], "inputs.original_image")
    garments_dir = relpath(job, inputs["garments_dir"], "inputs.garments_dir")
    model_path = resolve_archetype(models["archetype_id"], job.archetype_root)

    normalized_original = normalize_image(
        original,
        job.outputs_dir / "normalized" / "original.jpg",
    )
    normalized_dir = normalize_garment_folder(job, garments_dir)
    vto_dir = job.outputs_dir / "vto"
    vto_dir.mkdir(parents=True, exist_ok=True)

    if dry_run:
        mock_vto_for_garments(normalized_dir, vto_dir)
        skipped = []
    else:
        skipped = many_garments_to_one_body(
            normalized_dir,
            model_path,
            vto_dir,
            model=vto["model"],
            prompt=vto["prompt"],
            append_garment_name=vto["append_garment_name"],
        )

    reel_path = job.outputs_dir / "reel.mp4"
    build_reel(
        normalized_original,
        vto_dir,
        reel_path,
        original_image_description=reel["original_image_description"],
        original_image_credit=reel["original_image_credit"],
        body_type_intro=True,
        result_name_labels=reel["show_result_name_labels"],
        intro_duration=reel["intro_duration"],
        result_duration=reel["result_duration"],
        end_card_duration=reel["end_card_duration"],
    )
    return {"reel": str(reel_path), "vto_dir": str(vto_dir), "skipped_vto": skipped}


def mode_video(job, dry_run=False):
    inputs = job.config["inputs"]
    models = job.config["models"]
    video = job.config["video"]
    vto = vto_settings(job)
    reel = reel_settings(job)

    garment = relpath(job, inputs["garment_image"], "inputs.garment_image")
    model_path = resolve_archetype(models["archetype_id"], job.archetype_root)
    normalized_garment = normalize_garment_file(job, garment)

    vto_dir = job.outputs_dir / "vto"
    video_dir = job.outputs_dir / "video"
    vto_image = vto_dir / "tryon.jpg"
    video_path = video_dir / "tryon.mp4"
    video_prompt = prompt_text(video.get("prompt"), "video.prompt")
    video_duration = str(video.get("duration", "5"))

    if dry_run:
        mock_vto_for_models(normalized_garment, [model_path], vto_dir)
        first_mock = vto_dir / f"{Path(model_path).stem}.jpg"
        if first_mock.exists():
            first_mock.replace(vto_image)
        mock_video(vto_image, video_path, duration=min(float(video_duration), 3.0))
    else:
        one_garment_to_one_body(
            normalized_garment,
            model_path,
            vto_image,
            model=vto["model"],
            prompt=vto["prompt"],
            append_garment_name=vto["append_garment_name"],
        )
        generate_video(
            vto_image,
            video_path,
            video_prompt,
            model=video.get("model", DEFAULT_VIDEO_MODEL),
            duration=video_duration,
            generate_audio=video.get("generate_audio", False),
            negative_prompt=video.get("negative_prompt"),
            cfg_scale=video.get("cfg_scale"),
        )

    reel_path = job.outputs_dir / "reel.mp4"
    build_reel(
        normalized_garment,
        vto_dir,
        reel_path,
        featured_image=vto_image,
        featured_video=video_path,
        original_image_description=reel["original_image_description"],
        original_image_credit=reel["original_image_credit"],
        intro_duration=reel["intro_duration"],
        result_duration=reel["result_duration"],
        end_card_duration=reel["end_card_duration"],
    )
    return {"reel": str(reel_path), "vto_dir": str(vto_dir), "video": str(video_path)}


MODE_HANDLERS = {
    MODE_ONE_GARMENT_MULTIPLE_BODIES: mode_one_garment_multiple_bodies,
    MODE_MULTIPLE_GARMENTS_MULTIPLE_BODIES: mode_multiple_garments_multiple_bodies,
    MODE_ONE_BODY_MULTIPLE_GARMENTS: mode_one_body_multiple_garments,
    MODE_VIDEO: mode_video,
}


def run_job(job, dry_run=False):
    job.outputs_dir.mkdir(parents=True, exist_ok=True)
    job.logs_dir.mkdir(parents=True, exist_ok=True)
    write_status(job, "running", dry_run=dry_run)

    log_section("FASHIONBOT JOB")
    log_kv("Job ID", job.job_id)
    log_kv("Mode", job.mode)
    log_kv("Job folder", job.root)
    log_kv("Archetype folder", job.archetype_root)
    log_kv("Dry run", dry_run)

    handler = MODE_HANDLERS.get(job.mode)
    if handler is None:
        raise FashionbotError(f"Unsupported mode: {job.mode}")

    try:
        outputs = handler(job, dry_run=dry_run)
    except Exception as e:
        write_status(job, "failed", dry_run=dry_run, error=str(e))
        raise

    write_status(job, "done", dry_run=dry_run, outputs=outputs)
    return outputs
