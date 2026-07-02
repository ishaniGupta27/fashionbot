"""Silent reel builder kept for quick tests and legacy image/video assembly."""

from moviepy import ImageClip, VideoFileClip, concatenate_videoclips
import os
import argparse
import random
from PIL import Image, ImageDraw, ImageFont


VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
EXTRA_IMAGE = (
    "/Users/Himanshu/Documents/fashionbot/garments/extras/end.jpg"
)
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")
VIDEO_EXTENSIONS = (".mp4", ".mov", ".m4v")


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


def get_font(size):
    font_paths = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf"
    ]

    for font_path in font_paths:
        if os.path.exists(font_path):
            return ImageFont.truetype(font_path, size)

    return ImageFont.load_default()


def label_from_name(name):
    if not name.startswith("code_"):
        return None

    code = name[len("code_"):]
    return code.replace(":", "/").replace("_", "/")


def render_labeled_image(path, label, tmp_dir):
    if not label:
        return path

    os.makedirs(tmp_dir, exist_ok=True)

    img = Image.open(path).convert("RGB")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_size = max(22, img.width // 28)
    font = get_font(font_size)
    bbox = draw.textbbox((0, 0), label, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    padding_x = max(18, font_size // 2)
    padding_y = max(12, font_size // 3)
    margin = max(18, font_size // 2)
    right_inset = margin

    x1 = img.width - text_width - (padding_x * 2) - right_inset
    y1 = int(img.height * 0.28)
    x2 = img.width - right_inset
    y2 = y1 + text_height + (padding_y * 2)

    draw.rounded_rectangle(
        (x1, y1, x2, y2),
        radius=max(10, font_size // 4),
        fill=(0, 0, 0, 180)
    )
    draw.text(
        (x1 + padding_x, y1 + padding_y),
        label,
        font=font,
        fill=(255, 255, 255, 255)
    )

    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    output_name = (
        os.path.abspath(path)
        .replace(os.sep, "__")
        .replace(":", "")
        + ".labeled.jpg"
    )
    output_path = os.path.join(tmp_dir, output_name)
    img.save(output_path, quality=95)

    return output_path


def make_clip(path, duration, label=None, tmp_dir=None):
    if path.lower().endswith(VIDEO_EXTENSIONS):
        return (
            VideoFileClip(path)
            .resized(height=VIDEO_HEIGHT)
        )

    if label and tmp_dir:
        path = render_labeled_image(path, label, tmp_dir)

    return (
        ImageClip(path)
        .resized(height=VIDEO_HEIGHT)
        .with_duration(duration)
    )


def add_flat_result_clips(clips, dress_image, results_dir, tmp_dir):
    clips.append(
       make_clip(
           dress_image,
           2,
           label_from_name(os.path.splitext(os.path.basename(dress_image))[0]),
           tmp_dir
       )
    )

    media_files = get_media_files(results_dir)
    random.shuffle(media_files)

    for filename in media_files:
        clips.append(
            make_clip(
                os.path.join(results_dir, filename),
                1.0
            )
        )


def add_grouped_garment_clips(clips, garments_dir, results_dir, tmp_dir):
    garment_files = get_image_files(garments_dir)
    result_files = get_media_files(results_dir)

    print("\n🎞️ Grouped reel mode")
    print(f"Garments dir: {garments_dir}")
    print(f"Results dir: {results_dir}")
    print(f"Garment clips found: {len(garment_files)}")
    print(f"Result clips found: {len(result_files)}")

    for garment_file in garment_files:
        garment_stem = os.path.splitext(garment_file)[0]
        garment_name = garment_stem
        garment_label = label_from_name(garment_stem)
        garment_path = os.path.join(garments_dir, garment_file)

        print(f"\nAdding garment clip: {garment_file}")
        print(f"Label: {garment_label or '(none)'}")

        clips.append(
            make_clip(
                garment_path,
                1.0,
                garment_label,
                tmp_dir
            )
        )

        matching_results = [
            f for f in result_files
            if f.startswith(garment_name + "__")
        ]

        print(f"Matching result clips: {len(matching_results)}")

        for result_file in matching_results:
            print(f"Adding result clip: {result_file}")

            clips.append(
                make_clip(
                    os.path.join(results_dir, result_file),
                    1.0,
                    garment_label,
                    tmp_dir
                )
            )


def build_reel(dress_image, results_dir, output_file, garments_dir=None):
    clips = []
    tmp_dir = os.path.join(
        os.path.dirname(output_file),
        ".reel_labels"
    )

    if garments_dir:
        add_grouped_garment_clips(
            clips,
            garments_dir,
            results_dir,
            tmp_dir
        )
    else:
        add_flat_result_clips(
            clips,
            dress_image,
            results_dir,
            tmp_dir
        )

    if os.path.exists(EXTRA_IMAGE):
        clips.append(
            make_clip(
                EXTRA_IMAGE,
                1.0
            )
        )

    # Show original garment again at end
    #clips.append(
        #make_clip(dress_image, 1.5)
    #)

    video = concatenate_videoclips(
        clips,
        method="compose"
    )

    # Force Shorts/Reels size
    video = video.resized(
        (VIDEO_WIDTH, VIDEO_HEIGHT)
    )

    os.makedirs(
        os.path.dirname(output_file),
        exist_ok=True
    )

    video.write_videofile(
        output_file,
        fps=30,
        codec="libx264",
        audio=False
    )

    print(f"\n✅ Saved reel: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dress",
        required=True,
        help="Path to original garment image"
    )

    parser.add_argument(
        "--results",
        required=True,
        help="Folder containing generated archetype images"
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Output MP4 path"
    )

    parser.add_argument(
        "--garments",
        default=None,
        help="Folder containing original garment images"
    )

    args = parser.parse_args()

    build_reel(
        args.dress,
        args.results,
        args.output,
        garments_dir=args.garments
    )
