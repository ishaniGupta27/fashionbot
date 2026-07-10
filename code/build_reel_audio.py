"""Build final vertical reels from Fashionbot outputs.

The builder supports image reels, grouped batch reels, and featured video reels.
Featured video reels use the order: original image, VTO still, generated video,
then the optional end card. Audio can include an intro voiceover and delayed
background music.
"""

from moviepy import (
    ImageClip,
    AudioFileClip,
    CompositeAudioClip,
    VideoFileClip,
    concatenate_videoclips,
    afx,
    vfx
)

import os
import argparse
import random
from PIL import Image, ImageDraw, ImageFont


VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
DEFAULT_INTRO_DURATION = 1.8
DEFAULT_RESULT_DURATION = 1.0
DEFAULT_END_CARD_DURATION = 1.0
FEATURED_VIDEO_SPEED = 0.75

DEFAULT_AUDIO = (
    "/Users/Himanshu/Documents/fashionbot/Audio/Jazz.mp3"
)
DEFAULT_INTRO_VOICEOVER = (
    "/Users/Himanshu/Documents/fashionbot/Audio/voiceover_intro"
)
DEFAULT_MASCOT_IMAGE = (
    "/Users/Himanshu/Documents/fashionbot/garments/extras/mascot"
)
EXTRA_IMAGE = (
    "/Users/Himanshu/Documents/fashionbot/garments/extras/end.jpg"
)
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")
VIDEO_EXTENSIONS = (".mp4", ".mov", ".m4v")
AUDIO_EXTENSIONS = (".mp3", ".wav", ".m4a", ".aac")
TEXT_LAYOUT_DEFAULT = "default"
TEXT_LAYOUT_BODY_TYPE = "body_type"


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

    base, ext = os.path.splitext(path)

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

    base, ext = os.path.splitext(path)

    if ext:
        return None

    for image_ext in IMAGE_EXTENSIONS:
        candidate = path + image_ext

        if os.path.exists(candidate):
            return candidate

    return None


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


def display_name_from_filename(filename):
    stem = os.path.splitext(filename)[0]
    code_label = label_from_name(stem)

    if code_label:
        return code_label

    return (
        stem
        .replace("__", " ")
        .replace("_", " ")
        .replace("-", " ")
        .strip()
    )


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        candidate = word if not current_line else f"{current_line} {word}"
        bbox = draw.textbbox((0, 0), candidate, font=font)

        if bbox[2] - bbox[0] <= max_width or not current_line:
            current_line = candidate
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines


def render_labeled_image(
    path,
    label,
    tmp_dir,
    mascot_path=None,
    description=None,
    credit=None,
    text_layout=TEXT_LAYOUT_DEFAULT,
    side_label=None
):
    if (
        not label
        and not mascot_path
        and not description
        and not credit
        and not side_label
    ):
        return path

    os.makedirs(tmp_dir, exist_ok=True)

    img = Image.open(path).convert("RGB")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    if label:
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

    if mascot_path:
        mascot = Image.open(mascot_path).convert("RGBA")
        max_mascot_size = (
            int(img.width * 0.25),
            int(img.height * 0.22)
        )
        mascot.thumbnail(max_mascot_size, Image.LANCZOS)

        margin = max(28, img.width // 36)
        x = margin
        y = img.height - mascot.height - margin

        shadow = Image.new("RGBA", mascot.size, (0, 0, 0, 75))
        overlay.alpha_composite(
            shadow,
            (x + max(6, img.width // 180), y + max(6, img.width // 180))
        )
        overlay.alpha_composite(mascot, (x, y))

    if side_label:
        font_size = max(22, img.width // 34)
        font = get_font(font_size)
        max_width = int(img.width * 0.32)
        lines = wrap_text(draw, side_label, font, max_width)
        line_boxes = [
            draw.textbbox((0, 0), line, font=font)
            for line in lines
        ]
        text_width = max((box[2] - box[0] for box in line_boxes), default=0)
        line_height = max((box[3] - box[1] for box in line_boxes), default=font_size)
        line_gap = max(4, font_size // 5)
        text_height = (
            line_height * len(lines)
            + line_gap * max(len(lines) - 1, 0)
        )
        padding_x = max(16, font_size // 2)
        padding_y = max(12, font_size // 3)
        right_safe = max(120, int(img.width * 0.14))

        box_width = text_width + (padding_x * 2)
        box_height = text_height + (padding_y * 2)
        x2 = img.width - right_safe
        x1 = x2 - box_width
        y1 = int((img.height * 0.75) - (box_height / 2))
        y2 = y1 + box_height

        draw.rounded_rectangle(
            (x1, y1, x2, y2),
            radius=max(8, font_size // 4),
            fill=(0, 0, 0, 155)
        )

        text_y = y1 + padding_y
        for line in lines:
            draw.text(
                (x1 + padding_x, text_y),
                line,
                font=font,
                fill=(255, 255, 255, 240)
            )
            text_y += line_height + line_gap

    if description or credit:
        font_size = max(20, img.width // 36)
        description_font = get_font(max(font_size + 3, img.width // 32))
        credit_font = get_font(font_size)
        body_type_layout = text_layout == TEXT_LAYOUT_BODY_TYPE
        max_width = int(img.width * (0.78 if body_type_layout else 0.46))
        text_blocks = []

        if description:
            text_blocks.append((
                wrap_text(draw, description, description_font, max_width),
                description_font,
                (255, 255, 255, 245)
            ))

        if credit:
            text_blocks.append((
                wrap_text(
                    draw,
                    f"Image credit: {credit}",
                    credit_font,
                    max_width
                ),
                credit_font,
                (255, 255, 255, 230)
            ))

        text_width = 0
        text_height = 0
        line_gap = max(4, font_size // 5)
        block_gap = max(10, font_size // 2)

        for block_index, (lines, font, _) in enumerate(text_blocks):
            line_boxes = [
                draw.textbbox((0, 0), line, font=font)
                for line in lines
            ]
            line_width = max((box[2] - box[0] for box in line_boxes), default=0)
            line_height = max((box[3] - box[1] for box in line_boxes), default=font_size)

            text_width = max(text_width, line_width)
            text_height += line_height * len(lines)
            text_height += line_gap * max(len(lines) - 1, 0)

            if block_index < len(text_blocks) - 1:
                text_height += block_gap

        padding_x = max(18, font_size // 2)
        padding_y = max(12, font_size // 3)
        margin = max(22, img.width // 40)

        box_width = (
            img.width - (margin * 2)
            if body_type_layout
            else text_width + (padding_x * 2)
        )
        box_height = text_height + (padding_y * 2)

        if body_type_layout:
            x1 = margin
            x2 = img.width - margin
            y1 = int((img.height * 0.75) - (box_height / 2))
        else:
            x2 = img.width - margin
            x1 = x2 - box_width
            y1 = int((img.height * 0.75) - (box_height / 2))
            y2 = y1 + box_height

        y2 = y1 + box_height

        draw.rounded_rectangle(
            (x1, y1, x2, y2),
            radius=max(10, font_size // 4),
            fill=(0, 0, 0, 155)
        )

        text_y = y1 + padding_y
        for block_index, (lines, font, fill) in enumerate(text_blocks):
            line_boxes = [
                draw.textbbox((0, 0), line, font=font)
                for line in lines
            ]
            line_height = max((box[3] - box[1] for box in line_boxes), default=font_size)

            for line in lines:
                line_box = draw.textbbox((0, 0), line, font=font)
                line_width = line_box[2] - line_box[0]
                text_x = (
                    x1 + ((box_width - line_width) / 2)
                    if body_type_layout
                    else x1 + padding_x
                )
                draw.text(
                    (text_x, text_y),
                    line,
                    font=font,
                    fill=fill
                )
                text_y += line_height + line_gap

            if block_index < len(text_blocks) - 1:
                text_y += block_gap - line_gap

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


def make_clip(
    path,
    duration,
    label=None,
    tmp_dir=None,
    mascot_path=None,
    description=None,
    credit=None,
    text_layout=TEXT_LAYOUT_DEFAULT,
    side_label=None
):
    if path.lower().endswith(VIDEO_EXTENSIONS):
        return (
            VideoFileClip(path)
            .resized(height=VIDEO_HEIGHT)
        )

    if tmp_dir:
        path = render_labeled_image(
            path,
            label,
            tmp_dir,
            mascot_path,
            description,
            credit,
            text_layout,
            side_label
        )

    return (
        ImageClip(path)
        .resized(height=VIDEO_HEIGHT)
        .with_duration(duration)
    )


def add_flat_result_clips(
    clips,
    dress_image,
    results_dir,
    tmp_dir,
    intro_features=False,
    mascot_path=None,
    original_image_description=None,
    original_image_credit=None,
    original_image_text_layout=TEXT_LAYOUT_DEFAULT,
    result_name_labels=False,
    intro_duration=DEFAULT_INTRO_DURATION,
    result_duration=DEFAULT_RESULT_DURATION
):
    clips.append(
        make_clip(
            dress_image,
            intro_duration,
            label_from_name(os.path.splitext(os.path.basename(dress_image))[0]),
            tmp_dir,
            mascot_path if intro_features else None,
            original_image_description,
            original_image_credit,
            original_image_text_layout
        )
    )

    media_files = get_media_files(results_dir)
    random.shuffle(media_files)

    for filename in media_files:
        result_label = (
            display_name_from_filename(filename)
            if result_name_labels
            else None
        )

        clips.append(
            make_clip(
                os.path.join(
                    results_dir,
                    filename
                ),
                result_duration,
                tmp_dir=tmp_dir if result_label else None,
                side_label=result_label
            )
        )


def add_grouped_garment_clips(
    clips,
    garments_dir,
    results_dir,
    tmp_dir,
    original_image_description=None,
    original_image_credit=None,
    result_duration=DEFAULT_RESULT_DURATION
):
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
                result_duration,
                garment_label,
                tmp_dir,
                description=original_image_description,
                credit=original_image_credit
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
                    result_duration,
                    garment_label,
                    tmp_dir
                )
            )


def build_reel(
    dress_image,
    results_dir,
    output_file,
    garments_dir=None,
    featured_image=None,
    featured_video=None,
    intro_features=False,
    intro_voiceover=DEFAULT_INTRO_VOICEOVER,
    mascot_image=DEFAULT_MASCOT_IMAGE,
    music_file=DEFAULT_AUDIO,
    original_image_description=None,
    original_image_credit=None,
    body_type_intro=False,
    result_name_labels=False,
    intro_duration=DEFAULT_INTRO_DURATION,
    result_duration=DEFAULT_RESULT_DURATION,
    end_card_duration=DEFAULT_END_CARD_DURATION
):
    """Assemble the final reel from the selected presentation mode."""
    clips = []
    tmp_dir = os.path.join(
        os.path.dirname(output_file),
        ".reel_labels"
    )

    featured_mode = bool(featured_image or featured_video)
    audio_intro_mode = intro_features
    mascot_mode = featured_mode or intro_features
    mascot_path = resolve_image_file(mascot_image) if mascot_mode else None

    if featured_mode:
        clips.append(
            make_clip(
                dress_image,
                intro_duration,
                label_from_name(os.path.splitext(os.path.basename(dress_image))[0]),
                tmp_dir,
                mascot_path,
                original_image_description,
                original_image_credit
            )
        )

        if featured_image:
            print(f"Adding featured VTO image: {featured_image}")
            clips.append(
                make_clip(
                    featured_image,
                    result_duration
                )
            )

        if featured_video:
            print(f"Adding featured video: {featured_video}")
            clips.append(
                make_clip(featured_video, 1.0)
                .with_effects([
                    vfx.MultiplySpeed(FEATURED_VIDEO_SPEED)
                ])
            )

    elif garments_dir:
        add_grouped_garment_clips(
            clips,
            garments_dir,
            results_dir,
            tmp_dir,
            original_image_description,
            original_image_credit,
            result_duration
        )
    else:
        add_flat_result_clips(
            clips,
            dress_image,
            results_dir,
            tmp_dir,
            intro_features=intro_features,
            mascot_path=mascot_path,
            original_image_description=original_image_description,
            original_image_credit=original_image_credit,
            original_image_text_layout=(
                TEXT_LAYOUT_BODY_TYPE
                if body_type_intro
                else TEXT_LAYOUT_DEFAULT
            ),
            result_name_labels=result_name_labels,
            intro_duration=intro_duration,
            result_duration=result_duration
        )

    if os.path.exists(EXTRA_IMAGE):
        clips.append(
            make_clip(
                EXTRA_IMAGE,
                end_card_duration
            )
        )

    #
    # Build video
    #
    video = concatenate_videoclips(
        clips,
        method="compose"
    )

    video = video.resized(
        (VIDEO_WIDTH, VIDEO_HEIGHT)
    )

    #
    # Add audio if present
    #
    music_path = resolve_audio_file(music_file)
    intro_voiceover_path = resolve_audio_file(intro_voiceover)

    if music_path or (audio_intro_mode and intro_voiceover_path):
        print(
            "\n🎵 Adding audio"
        )

        audio_clips = []
        music_start = intro_duration if audio_intro_mode else 0

        if audio_intro_mode and intro_voiceover_path:
            print(f"Voiceover intro: {intro_voiceover_path}")

            voiceover = AudioFileClip(
                intro_voiceover_path
            )

            voiceover_duration = min(
                voiceover.duration,
                intro_duration
            )

            audio_clips.append(
                voiceover.subclipped(
                    0,
                    voiceover_duration
                )
            )

        if music_path:
            print(f"Background music: {music_path}")
            print(f"Background music starts at: {music_start}s")

            music_duration = max(
                video.duration - music_start,
                0
            )

            if music_duration > 0:
                audio = AudioFileClip(
                    music_path
                )

                audio = audio.with_effects([
                    afx.AudioLoop(
                        duration=music_duration
                    )
                ])

                audio = audio.subclipped(
                    0,
                    music_duration
                ).with_start(
                    music_start
                )

                audio_clips.append(audio)

        if audio_clips:
            video = video.with_audio(
                CompositeAudioClip(audio_clips)
            )

    else:
        print(
            "\n⚠️ Audio file not found. Creating silent video."
        )

    #
    # Output
    #
    os.makedirs(
        os.path.dirname(output_file),
        exist_ok=True
    )

    video.write_videofile(
        output_file,
        fps=30,
        codec="libx264",
        audio_codec="aac"
    )

    print(
        f"\n✅ Saved reel: {output_file}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dress",
        required=True
    )

    parser.add_argument(
        "--results",
        required=True
    )

    parser.add_argument(
        "--output",
        required=True
    )

    parser.add_argument(
        "--garments",
        default=None
    )

    parser.add_argument(
        "--featured-image",
        default=None
    )

    parser.add_argument(
        "--featured-video",
        default=None
    )

    parser.add_argument(
        "--intro-features",
        action="store_true",
        help="Use intro voiceover/mascot on the opening garment image."
    )

    parser.add_argument(
        "--intro-voiceover",
        default=DEFAULT_INTRO_VOICEOVER
    )

    parser.add_argument(
        "--mascot-image",
        default=DEFAULT_MASCOT_IMAGE
    )

    parser.add_argument(
        "--original-image-description",
        default=None
    )

    parser.add_argument(
        "--original-image-credit",
        default=None
    )

    parser.add_argument(
        "--body-type-intro",
        action="store_true",
        help="Use centered Mode 4 text treatment for the original image."
    )

    parser.add_argument(
        "--result-name-labels",
        action="store_true",
        help="Overlay generated result filenames as garment labels."
    )

    parser.add_argument(
        "--intro-duration",
        type=float,
        default=DEFAULT_INTRO_DURATION
    )

    parser.add_argument(
        "--result-duration",
        type=float,
        default=DEFAULT_RESULT_DURATION
    )

    parser.add_argument(
        "--end-card-duration",
        type=float,
        default=DEFAULT_END_CARD_DURATION
    )

    args = parser.parse_args()

    build_reel(
        args.dress,
        args.results,
        args.output,
        garments_dir=args.garments,
        featured_image=args.featured_image,
        featured_video=args.featured_video,
        intro_features=args.intro_features,
        intro_voiceover=args.intro_voiceover,
        mascot_image=args.mascot_image,
        original_image_description=args.original_image_description,
        original_image_credit=args.original_image_credit,
        body_type_intro=args.body_type_intro,
        result_name_labels=args.result_name_labels,
        intro_duration=args.intro_duration,
        result_duration=args.result_duration,
        end_card_duration=args.end_card_duration
    )
