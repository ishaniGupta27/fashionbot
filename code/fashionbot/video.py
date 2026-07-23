from pathlib import Path

from .errors import FashionbotError
from .files import output_exists
from .secrets import export_secret_to_env
from .settings import DEFAULT_VIDEO_MODEL


def ensure_fal_key():
    export_secret_to_env("FAL_KEY", required=True)


def generate_video(
    source_image,
    output_path,
    prompt,
    model=DEFAULT_VIDEO_MODEL,
    duration="5",
    generate_audio=False,
    negative_prompt=None,
    cfg_scale=None,
):
    ensure_fal_key()

    try:
        import fal_client
        import requests
    except ImportError as e:
        raise FashionbotError(
            "Missing fal.ai dependencies. Activate the venv or install project dependencies."
        ) from e

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_exists(output_path):
        print(f"SKIP already exists: {output_path}")
        return output_path

    print("Uploading source image for video...")
    start_image_url = fal_client.upload_file(str(source_image))

    arguments = {
        "start_image_url": start_image_url,
        "prompt": prompt,
        "duration": str(duration),
        "generate_audio": bool(generate_audio),
    }

    if negative_prompt:
        arguments["negative_prompt"] = negative_prompt

    if cfg_scale is not None:
        arguments["cfg_scale"] = cfg_scale

    print(f"Calling video model: {model}")
    result = fal_client.subscribe(model, arguments=arguments, with_logs=True)
    video_url = result["video"]["url"]

    print("Downloading generated video...")
    response = requests.get(video_url)
    response.raise_for_status()

    with output_path.open("wb") as f:
        f.write(response.content)

    return output_path
