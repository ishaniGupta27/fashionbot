"""Generate one image-to-video asset from a selected VTO still.

The pipeline uses this only for the single-garment video mode because video
calls are costly. The script asks for confirmation before calling fal.ai.
"""

import argparse
import os

import fal_client
import requests

from env_config import load_dotenv_if_present


DEFAULT_VIDEO_MODEL = "fal-ai/kling-video/v3/standard/image-to-video"


def output_exists(path):
    return os.path.isfile(path) and os.path.getsize(path) > 0


def confirm_video_call(source_image, output_path):
    print("\nVideo generation is enabled.")
    print(f"Source image: {source_image}")
    print(f"Output video: {output_path}")

    answer = input("This will make 1 video generation call. Continue? [y/N]: ")
    answer = answer.strip().lower()

    if answer not in ("y", "yes"):
        raise RuntimeError("Cancelled before starting video generation.")


def generate_video(
    source_image,
    output_path,
    prompt,
    model=DEFAULT_VIDEO_MODEL,
    duration="5",
    generate_audio=False,
    negative_prompt=None,
    cfg_scale=None
):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if output_exists(output_path):
        print(f"SKIP already exists: {output_path}")
        return

    confirm_video_call(source_image, output_path)

    print("\nUploading source image for video...")
    start_image_url = fal_client.upload_file(source_image)

    arguments = {
        "start_image_url": start_image_url,
        "prompt": prompt,
        "duration": str(duration),
        "generate_audio": bool(generate_audio)
    }

    if negative_prompt:
        arguments["negative_prompt"] = negative_prompt

    if cfg_scale is not None:
        arguments["cfg_scale"] = cfg_scale

    print(f"Calling video model: {model}")

    result = fal_client.subscribe(
        model,
        arguments=arguments,
        with_logs=True
    )

    video_url = result["video"]["url"]

    print("Downloading generated video...")
    response = requests.get(video_url)
    response.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(response.content)

    print(f"Saved video: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--source-image", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--model", default=DEFAULT_VIDEO_MODEL)
    parser.add_argument("--duration", default="5")
    parser.add_argument("--generate-audio", action="store_true")
    parser.add_argument("--negative-prompt", default=None)
    parser.add_argument("--cfg-scale", type=float, default=None)

    args = parser.parse_args()

    load_dotenv_if_present()

    if "FAL_KEY" not in os.environ:
        raise RuntimeError(
            "FAL_KEY not found. Run: export FAL_KEY='your_key' "
            "or add FAL_KEY=your_key to code/.env"
        )

    generate_video(
        args.source_image,
        args.output,
        args.prompt,
        model=args.model,
        duration=args.duration,
        generate_audio=args.generate_audio,
        negative_prompt=args.negative_prompt,
        cfg_scale=args.cfg_scale
    )
