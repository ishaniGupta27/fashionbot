from pathlib import Path

from PIL import Image

from .errors import FashionbotError, VTOContentPolicyError, VTOProviderError
from .files import display_name, image_files, output_exists
from .secrets import export_secret_to_env


FASHN_MODEL_ID = "fal-ai/fashn/tryon/v1.5"
FLUX_MODEL_ID = "fal-ai/flux-pro/v1/vto"
DEFAULT_FLUX_PROMPT = "A natural front-facing studio shot. The garment is worn naturally."
OUTPUT_EXTENSION = ".jpg"
MAX_UPLOAD_HEIGHT = 1024
UPLOAD_JPEG_QUALITY = 90
MODEL_FRAME_SCALE = 0.94
MODEL_TOP_PADDING_RATIO = 0.055
MODEL_FRAME_PROMPT = (
    "Keep the full body centered with comfortable headroom above the hair "
    "and visible feet. Do not crop the head or feet."
)


def build_fashn_arguments(model_url, garment_url):
    return {
        "model_image": model_url,
        "garment_image": garment_url,
        "category": "auto",
        "mode": "balanced",
        "garment_photo_type": "auto",
        "num_samples": 1,
        "segmentation_free": True,
        "output_format": "jpeg",
    }


def build_flux_arguments(model_url, garment_url, prompt):
    return {
        "prompt": prompt,
        "human_image_url": model_url,
        "garment_image_url": garment_url,
        "output_format": "jpeg",
    }


def resize_for_vto(path, tmp_dir, prefix=""):
    tmp_dir = Path(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    img = Image.open(path).convert("RGB")

    if img.height > MAX_UPLOAD_HEIGHT:
        ratio = MAX_UPLOAD_HEIGHT / img.height
        img = img.resize((int(img.width * ratio), MAX_UPLOAD_HEIGHT), Image.LANCZOS)

    output_name = prefix + Path(path).stem + ".vto.jpg"
    output_path = tmp_dir / output_name
    img.save(output_path, quality=UPLOAD_JPEG_QUALITY, optimize=True)
    return output_path


def resize_model_for_vto(path, tmp_dir, prefix=""):
    output_path = resize_for_vto(path, tmp_dir, prefix=prefix)
    img = Image.open(output_path).convert("RGB")
    background = img.getpixel((0, 0))
    framed = Image.new("RGB", img.size, background)
    new_size = (
        int(img.width * MODEL_FRAME_SCALE),
        int(img.height * MODEL_FRAME_SCALE),
    )
    resized = img.resize(new_size, Image.LANCZOS)
    x = (img.width - resized.width) // 2
    y = int(img.height * MODEL_TOP_PADDING_RATIO)
    framed.paste(resized, (x, y))
    framed.save(output_path, quality=UPLOAD_JPEG_QUALITY, optimize=True)
    return output_path


def prompt_for_garment(prompt, garment_path, append_garment_name=False):
    base_prompt = prompt or DEFAULT_FLUX_PROMPT

    if append_garment_name:
        garment_name = display_name(garment_path)
        if garment_name:
            base_prompt = f"{base_prompt} Garment name: {garment_name}."

    return f"{base_prompt} {MODEL_FRAME_PROMPT}"


def is_fal_auth_error(error):
    status_code = getattr(error, "status_code", None)
    response = getattr(error, "response", None)

    if response is not None:
        status_code = getattr(response, "status_code", status_code)

    if status_code in (401, 403):
        return True

    message = str(error).lower()
    return (
        "403 forbidden" in message
        or "401 unauthorized" in message
        or "storage/auth/token" in message
    )


def fal_auth_error_message():
    return (
        "fal.ai authentication failed while uploading an image. "
        "Your FAL_KEY is present, but fal.ai rejected it. "
        "Export a valid key in this terminal with: export FAL_KEY='your_key' "
        "or save it in code/.env as FAL_KEY=your_key."
    )


def is_fal_content_policy_error(error):
    message = str(error).lower()
    return (
        "content_policy_violation" in message
        or "content policy" in message
        or "content checker" in message
    )


def fal_content_policy_message(garment_path, model_path):
    return (
        "fal.ai rejected this VTO pair because its content checker flagged "
        "the prompt or one of the uploaded images. "
        f"Garment: {Path(garment_path).name}. "
        f"Model: {Path(model_path).name}."
    )


def clean_provider_message(error):
    message = str(error).strip()
    if len(message) > 500:
        message = message[:500].rstrip() + "..."
    return message


def build_tryon_arguments(model_url, garment_url, model, prompt):
    if model == "flux":
        return (
            FLUX_MODEL_ID,
            build_flux_arguments(model_url, garment_url, prompt or DEFAULT_FLUX_PROMPT),
        )

    return FASHN_MODEL_ID, build_fashn_arguments(model_url, garment_url)


def ensure_fal_key():
    export_secret_to_env("FAL_KEY", required=True)


def run_tryon_pair(
    garment_path,
    model_path,
    output_path,
    tmp_dir,
    model="fash",
    prompt=None,
    append_garment_name=False,
):
    ensure_fal_key()

    try:
        import fal_client
        import requests
    except ImportError as e:
        raise FashionbotError(
            "Missing fal.ai dependencies. Activate the venv or install project dependencies."
        ) from e

    resized_garment_path = resize_for_vto(garment_path, tmp_dir, prefix="garment_")
    resized_model_path = resize_model_for_vto(model_path, tmp_dir, prefix="model_")

    try:
        garment_url = fal_client.upload_file(str(resized_garment_path))
        model_url = fal_client.upload_file(str(resized_model_path))

        model_id, arguments = build_tryon_arguments(
            model_url,
            garment_url,
            model,
            prompt_for_garment(prompt, garment_path, append_garment_name),
        )

        result = fal_client.subscribe(model_id, arguments=arguments, with_logs=False)
        output_url = result["images"][0]["url"]
        response = requests.get(output_url)
        response.raise_for_status()
    except Exception as e:
        if is_fal_auth_error(e):
            raise FashionbotError(fal_auth_error_message()) from e
        if is_fal_content_policy_error(e):
            raise VTOContentPolicyError(
                fal_content_policy_message(garment_path, model_path)
            ) from e
        raise VTOProviderError(f"fal.ai VTO request failed: {clean_provider_message(e)}") from e

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as f:
        f.write(response.content)


def one_garment_to_many_bodies(
    garment_path,
    model_paths,
    output_dir,
    model="fash",
    prompt=None,
    append_garment_name=False,
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = output_dir / ".vto_uploads"
    skipped = []

    for model_path in model_paths:
        output_path = output_dir / f"{Path(model_path).stem}{OUTPUT_EXTENSION}"
        if output_exists(output_path):
            print(f"SKIP already exists: {output_path}")
            continue

        print(f"Processing {Path(model_path).name}")
        try:
            run_tryon_pair(
                garment_path,
                model_path,
                output_path,
                tmp_dir,
                model=model,
                prompt=prompt,
                append_garment_name=append_garment_name,
            )
        except VTOContentPolicyError as e:
            print(f"SKIP content policy: {Path(model_path).name}")
            print(f"Reason: {e}")
            skipped.append({"model": Path(model_path).name, "reason": str(e)})

    return skipped


def many_garments_to_one_body(
    garments_dir,
    model_path,
    output_dir,
    model="fash",
    prompt=None,
    append_garment_name=False,
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = output_dir / ".vto_uploads"
    skipped = []

    for garment_path in image_files(garments_dir):
        output_path = output_dir / f"{garment_path.stem}{OUTPUT_EXTENSION}"
        if output_exists(output_path):
            print(f"SKIP already exists: {output_path}")
            continue

        print(f"Processing {garment_path.name}")
        try:
            run_tryon_pair(
                garment_path,
                model_path,
                output_path,
                tmp_dir,
                model=model,
                prompt=prompt,
                append_garment_name=append_garment_name,
            )
        except VTOContentPolicyError as e:
            print(f"SKIP content policy: {garment_path.name}")
            print(f"Reason: {e}")
            skipped.append({"garment": garment_path.name, "reason": str(e)})

    return skipped


def many_garments_to_many_bodies(
    garments_dir,
    model_paths,
    output_dir,
    model="fash",
    prompt=None,
    append_garment_name=False,
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = output_dir / ".vto_uploads"
    skipped = []

    for garment_path in image_files(garments_dir):
        for model_path in model_paths:
            output_name = f"{garment_path.stem}__{Path(model_path).stem}{OUTPUT_EXTENSION}"
            output_path = output_dir / output_name

            if output_exists(output_path):
                print(f"SKIP already exists: {output_path}")
                continue

            print(f"Processing {garment_path.name} on {Path(model_path).name}")
            try:
                run_tryon_pair(
                    garment_path,
                    model_path,
                    output_path,
                    tmp_dir,
                    model=model,
                    prompt=prompt,
                    append_garment_name=append_garment_name,
                )
            except VTOContentPolicyError as e:
                print(f"SKIP content policy: {garment_path.name} on {Path(model_path).name}")
                print(f"Reason: {e}")
                skipped.append({
                    "garment": garment_path.name,
                    "model": Path(model_path).name,
                    "reason": str(e),
                })

    return skipped


def one_garment_to_one_body(
    garment_path,
    model_path,
    output_path,
    model="fash",
    prompt=None,
    append_garment_name=False,
):
    output_path = Path(output_path)
    if output_exists(output_path):
        print(f"SKIP already exists: {output_path}")
        return

    run_tryon_pair(
        garment_path,
        model_path,
        output_path,
        output_path.parent / ".vto_uploads",
        model=model,
        prompt=prompt,
        append_garment_name=append_garment_name,
    )
