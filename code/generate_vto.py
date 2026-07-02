"""Generate virtual try-on images through fal.ai.

Supports the three VTO shapes used by the pipeline:
- one garment to many model images
- many garments to many model images
- one garment to one model image, used as the video source still
"""

import os
import argparse
import requests
import fal_client
from PIL import Image


FASHN_MODEL_ID = "fal-ai/fashn/tryon/v1.5"
FLUX_MODEL_ID = "fal-ai/flux-pro/v1/vto"
DEFAULT_FLUX_PROMPT = "A natural front-facing studio shot. The garment is worn naturally."
OUTPUT_EXTENSION = ".jpg"
MAX_UPLOAD_HEIGHT = 1024
UPLOAD_JPEG_QUALITY = 90
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")
CONFIRM_CALL_THRESHOLD = 10


def build_fashn_arguments(model_url, garment_url):
    return {
        "model_image": model_url,
        "garment_image": garment_url,
        "category": "auto",
        "mode": "balanced",
        "garment_photo_type": "auto",
        "num_samples": 1,
        "segmentation_free": True,
        "output_format": "jpeg"
    }


def build_flux_arguments(model_url, garment_url, prompt):
    return {
        "prompt": prompt,
        "human_image_url": model_url,
        "garment_image_url": garment_url,
        "output_format": "jpeg"
    }


def resize_for_vto(path, tmp_dir, prefix=""):
    os.makedirs(tmp_dir, exist_ok=True)

    img = Image.open(path)
    img = img.convert("RGB")

    if img.height > MAX_UPLOAD_HEIGHT:
        ratio = MAX_UPLOAD_HEIGHT / img.height
        img = img.resize(
            (int(img.width * ratio), MAX_UPLOAD_HEIGHT),
            Image.LANCZOS
        )

    output_name = (
        prefix
        + os.path.splitext(os.path.basename(path))[0]
        + ".vto.jpg"
    )
    output_path = os.path.join(tmp_dir, output_name)
    img.save(output_path, quality=UPLOAD_JPEG_QUALITY, optimize=True)

    return output_path


def get_image_files(image_dir):
    return sorted([
        f for f in os.listdir(image_dir)
        if f.lower().endswith(IMAGE_EXTENSIONS)
    ])


def confirm_vto_calls(total_calls):
    if total_calls <= CONFIRM_CALL_THRESHOLD:
        return

    answer = input(
        f"\nThis will make {total_calls} VTO calls. Continue? [y/N]: "
    ).strip().lower()

    if answer not in ("y", "yes"):
        raise RuntimeError("Cancelled before starting VTO calls.")


def output_exists(path):
    return os.path.isfile(path) and os.path.getsize(path) > 0


def log_skip(output_path):
    print(f"SKIP already exists: {output_path}")


def build_tryon_arguments(model_url, garment_url, model, prompt):
    if model == "flux":
        return (
            FLUX_MODEL_ID,
            build_flux_arguments(
                model_url,
                garment_url,
                prompt or DEFAULT_FLUX_PROMPT
            )
        )

    return (
        FASHN_MODEL_ID,
        build_fashn_arguments(model_url, garment_url)
    )


def run_tryon_pair(
    garment_path,
    model_path,
    output_path,
    tmp_dir,
    model="fash",
    prompt=None
):
    """Upload one garment/model pair, call the selected VTO API, save JPEG."""
    resized_garment_path = resize_for_vto(
        garment_path,
        tmp_dir,
        prefix="garment_"
    )
    resized_model_path = resize_for_vto(
        model_path,
        tmp_dir,
        prefix="model_"
    )

    garment_url = fal_client.upload_file(resized_garment_path)
    model_url = fal_client.upload_file(resized_model_path)

    model_id, arguments = build_tryon_arguments(
        model_url,
        garment_url,
        model,
        prompt
    )

    result = fal_client.subscribe(
        model_id,
        arguments=arguments,
        with_logs=False
    )

    output_url = result["images"][0]["url"]

    response = requests.get(output_url)
    response.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(response.content)


def generate_vto(dress_path, models_dir, output_dir, model="fash", prompt=None):
    os.makedirs(output_dir, exist_ok=True)
    tmp_dir = os.path.join(output_dir, ".vto_uploads")

    image_files = get_image_files(models_dir)

    if not image_files:
        raise RuntimeError(f"No model images found in {models_dir}")

    pending_jobs = []

    for filename in image_files:
        model_path = os.path.join(models_dir, filename)
        output_name = os.path.splitext(filename)[0] + OUTPUT_EXTENSION
        output_path = os.path.join(output_dir, output_name)

        if output_exists(output_path):
            log_skip(output_path)
            continue

        pending_jobs.append((filename, model_path, output_path))

    print("\nDetected mode: one garment to many models")
    print("Garments found: 1")
    print(f"Found {len(image_files)} model images")
    print(f"Existing outputs skipped: {len(image_files) - len(pending_jobs)}")
    print(f"VTO calls to make: {len(pending_jobs)}")

    confirm_vto_calls(len(pending_jobs))

    for filename, model_path, output_path in pending_jobs:
        try:
            print(f"\nProcessing {filename}")

            run_tryon_pair(
                dress_path,
                model_path,
                output_path,
                tmp_dir,
                model=model,
                prompt=prompt
            )

            print(f"Saved: {output_path}")

        except Exception as e:
            print(f"FAILED: {filename}")
            print(e)

    print("\nDone!")


def generate_vto_pair(
    dress_path,
    model_image_path,
    output_path,
    model="fash",
    prompt=None
):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    tmp_dir = os.path.join(os.path.dirname(output_path), ".vto_uploads")

    print("\nDetected mode: one garment to one model")
    print("Garments found: 1")
    print("Models found: 1")
    print("Total VTO calls: 1")
    print(f"Garment: {dress_path}")
    print(f"Model image: {model_image_path}")
    print(f"Output image: {output_path}")

    if output_exists(output_path):
        log_skip(output_path)
        print("Existing outputs skipped: 1")
        print("VTO calls to make: 0")
        print("\nDone!")
        return

    print("Existing outputs skipped: 0")
    print("VTO calls to make: 1")

    run_tryon_pair(
        dress_path,
        model_image_path,
        output_path,
        tmp_dir,
        model=model,
        prompt=prompt
    )

    print(f"Saved: {output_path}")
    print("\nDone!")


def generate_vto_grid(garments_dir, models_dir, output_dir, model="fash", prompt=None):
    os.makedirs(output_dir, exist_ok=True)
    tmp_dir = os.path.join(output_dir, ".vto_uploads")

    garment_files = get_image_files(garments_dir)
    model_files = get_image_files(models_dir)
    if not garment_files:
        raise RuntimeError(f"No garment images found in {garments_dir}")

    if not model_files:
        raise RuntimeError(f"No model images found in {models_dir}")

    total_pairs = len(garment_files) * len(model_files)
    pending_jobs = []

    for garment_file in garment_files:
        garment_path = os.path.join(garments_dir, garment_file)
        garment_name = os.path.splitext(garment_file)[0]

        for model_file in model_files:
            model_path = os.path.join(models_dir, model_file)
            model_name = os.path.splitext(model_file)[0]

            output_name = (
                f"{garment_name}__{model_name}{OUTPUT_EXTENSION}"
            )
            output_path = os.path.join(output_dir, output_name)

            if output_exists(output_path):
                log_skip(output_path)
                continue

            pending_jobs.append((
                garment_file,
                model_file,
                garment_path,
                model_path,
                output_path
            ))

    print("\nDetected mode: many garments to many models")
    print(f"Garments found: {len(garment_files)}")
    print(f"Models found: {len(model_files)}")
    print(f"Existing outputs skipped: {total_pairs - len(pending_jobs)}")
    print(f"VTO calls to make: {len(pending_jobs)}")

    confirm_vto_calls(len(pending_jobs))

    for (
        garment_file,
        model_file,
        garment_path,
        model_path,
        output_path
    ) in pending_jobs:
        try:
            print(f"\nProcessing {garment_file} on {model_file}")

            run_tryon_pair(
                garment_path,
                model_path,
                output_path,
                tmp_dir,
                model=model,
                prompt=prompt
            )

            print(f"Saved: {output_path}")

        except Exception as e:
            print(f"FAILED: {garment_file} on {model_file}")
            print(e)

    print("\nDone!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dress",
        default=None,
        help="Path to garment image"
    )

    parser.add_argument(
        "--garments",
        default=None,
        help="Directory containing garment images"
    )

    parser.add_argument(
        "--models",
        default=None,
        help="Directory containing archetype images"
    )

    parser.add_argument(
        "--model-image",
        default=None,
        help="Single model image path"
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Directory where results will be saved"
    )

    parser.add_argument(
        "--model",
        choices=["fash", "flux"],
        default="fash",
        help="VTO model to use. Default: fash"
    )

    parser.add_argument(
        "--prompt",
        default=None,
        help="Prompt to use with --model flux"
    )

    args = parser.parse_args()

    if "FAL_KEY" not in os.environ:
        raise RuntimeError(
            "FAL_KEY not found. Run: export FAL_KEY='your_key'"
        )

    if args.model_image:
        if not args.dress:
            raise RuntimeError("--dress is required with --model-image")

        generate_vto_pair(
            args.dress,
            args.model_image,
            args.output,
            model=args.model,
            prompt=args.prompt
        )
    elif args.garments:
        if not args.models:
            raise RuntimeError("--models is required with --garments")

        generate_vto_grid(
            args.garments,
            args.models,
            args.output,
            model=args.model,
            prompt=args.prompt
        )
    elif args.dress:
        if not args.models:
            raise RuntimeError("--models is required with --dress")

        generate_vto(
            args.dress,
            args.models,
            args.output,
            model=args.model,
            prompt=args.prompt
        )
    else:
        raise RuntimeError("Provide either --dress or --garments")
