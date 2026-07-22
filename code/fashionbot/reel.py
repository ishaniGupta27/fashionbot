import random
from pathlib import Path

from moviepy import (
    AudioFileClip,
    CompositeAudioClip,
    ImageClip,
    VideoFileClip,
    afx,
    concatenate_videoclips,
    vfx,
)
from PIL import Image, ImageDraw

from .files import display_name, image_files, media_files, resolve_audio_file, resolve_image_file
from .fonts import bold_font
from .settings import (
    DEFAULT_AUDIO,
    DEFAULT_END_CARD,
    DEFAULT_END_CARD_DURATION,
    DEFAULT_INTRO_DURATION,
    DEFAULT_INTRO_VOICEOVER,
    DEFAULT_MASCOT_IMAGE,
    DEFAULT_RESULT_DURATION,
    VIDEO_EXTENSIONS,
    VIDEO_HEIGHT,
    VIDEO_WIDTH,
)


FEATURED_VIDEO_SPEED = 0.75
TEXT_LAYOUT_DEFAULT = "default"
TEXT_LAYOUT_BODY_TYPE = "body_type"


def get_font(size):
    return bold_font(size)


def render_canvas(img):
    if img.size == (VIDEO_WIDTH, VIDEO_HEIGHT):
        return img

    return img.resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.Resampling.LANCZOS)


def label_from_name(name):
    if not name.startswith("code_"):
        return None

    return name[len("code_") :].replace(":", "/").replace("_", "/")


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
    side_label=None,
):
    if not label and not mascot_path and not description and not credit and not side_label:
        return path

    tmp_dir = Path(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    img = render_canvas(Image.open(path).convert("RGB"))
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
        x1 = img.width - text_width - (padding_x * 2) - margin
        y1 = int(img.height * 0.28)
        x2 = img.width - margin
        y2 = y1 + text_height + (padding_y * 2)
        draw.rounded_rectangle((x1, y1, x2, y2), radius=10, fill=(0, 0, 0, 180))
        draw.text((x1 + padding_x, y1 + padding_y), label, font=font, fill=(255, 255, 255, 255))

    if mascot_path:
        mascot = Image.open(mascot_path).convert("RGBA")
        mascot.thumbnail((int(img.width * 0.25), int(img.height * 0.22)), Image.LANCZOS)
        margin = max(28, img.width // 36)
        x = margin
        y = img.height - mascot.height - margin
        shadow = Image.new("RGBA", mascot.size, (0, 0, 0, 75))
        overlay.alpha_composite(shadow, (x + 6, y + 6))
        overlay.alpha_composite(mascot, (x, y))

    if side_label:
        font_size = max(48, img.width // 22)
        font = get_font(font_size)
        max_width = int(img.width * 0.32)
        lines = wrap_text(draw, side_label, font, max_width)
        line_boxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
        text_width = max((box[2] - box[0] for box in line_boxes), default=0)
        line_height = max((box[3] - box[1] for box in line_boxes), default=font_size)
        line_gap = max(4, font_size // 5)
        text_height = line_height * len(lines) + line_gap * max(len(lines) - 1, 0)
        padding_x = max(16, font_size // 2)
        padding_y = max(12, font_size // 3)
        right_safe = max(120, int(img.width * 0.14))
        box_width = text_width + (padding_x * 2)
        box_height = text_height + (padding_y * 2)
        x2 = img.width - right_safe
        x1 = x2 - box_width
        y1 = int((img.height * 0.75) - (box_height / 2))
        y2 = y1 + box_height
        draw.rounded_rectangle((x1, y1, x2, y2), radius=8, fill=(0, 0, 0, 155))

        text_y = y1 + padding_y
        for line in lines:
            draw.text((x1 + padding_x, text_y), line, font=font, fill=(255, 255, 255, 240))
            text_y += line_height + line_gap

    if description or credit:
        font_size = max(20, img.width // 36)
        description_font = get_font(max(font_size + 3, img.width // 32))
        credit_font = get_font(font_size)
        body_type_layout = text_layout == TEXT_LAYOUT_BODY_TYPE
        max_width = int(img.width * (0.78 if body_type_layout else 0.46))
        text_blocks = []

        if description:
            text_blocks.append((wrap_text(draw, description, description_font, max_width), description_font, (255, 255, 255, 245)))

        if credit:
            text_blocks.append((wrap_text(draw, f"Image credit: {credit}", credit_font, max_width), credit_font, (255, 255, 255, 230)))

        text_width = 0
        text_height = 0
        line_gap = max(4, font_size // 5)
        block_gap = max(10, font_size // 2)

        for block_index, (lines, font, _) in enumerate(text_blocks):
            line_boxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
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
        box_width = img.width - (margin * 2) if body_type_layout else text_width + (padding_x * 2)
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
        draw.rounded_rectangle((x1, y1, x2, y2), radius=10, fill=(0, 0, 0, 155))

        text_y = y1 + padding_y
        for block_index, (lines, font, fill) in enumerate(text_blocks):
            line_boxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
            line_height = max((box[3] - box[1] for box in line_boxes), default=font_size)

            for line in lines:
                line_box = draw.textbbox((0, 0), line, font=font)
                line_width = line_box[2] - line_box[0]
                text_x = x1 + ((box_width - line_width) / 2) if body_type_layout else x1 + padding_x
                draw.text((text_x, text_y), line, font=font, fill=fill)
                text_y += line_height + line_gap

            if block_index < len(text_blocks) - 1:
                text_y += block_gap - line_gap

    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    output_name = str(Path(path).resolve()).replace("/", "__").replace(":", "") + ".labeled.jpg"
    output_path = tmp_dir / output_name
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
    side_label=None,
):
    path = Path(path)
    if path.suffix.lower() in VIDEO_EXTENSIONS:
        return VideoFileClip(str(path)).resized(height=VIDEO_HEIGHT)

    if tmp_dir:
        path = render_labeled_image(
            path,
            label,
            tmp_dir,
            mascot_path,
            description,
            credit,
            text_layout,
            side_label,
        )

    return ImageClip(str(path)).resized(height=VIDEO_HEIGHT).with_duration(duration)


def add_flat_result_clips(
    clips,
    intro_image,
    results_dir,
    tmp_dir,
    intro_features=False,
    mascot_path=None,
    original_image_description=None,
    original_image_credit=None,
    original_image_text_layout=TEXT_LAYOUT_DEFAULT,
    result_name_labels=False,
    intro_duration=DEFAULT_INTRO_DURATION,
    result_duration=DEFAULT_RESULT_DURATION,
):
    clips.append(
        make_clip(
            intro_image,
            intro_duration,
            label_from_name(Path(intro_image).stem),
            tmp_dir,
            mascot_path if intro_features else None,
            original_image_description,
            original_image_credit,
            original_image_text_layout,
        )
    )

    result_files = media_files(results_dir)
    random.shuffle(result_files)

    for result_file in result_files:
        result_label = display_name(result_file.name) if result_name_labels else None
        clips.append(
            make_clip(
                result_file,
                result_duration,
                tmp_dir=tmp_dir if result_label else None,
                side_label=result_label,
            )
        )


def add_grouped_garment_clips(
    clips,
    garments_dir,
    results_dir,
    tmp_dir,
    original_image_description=None,
    original_image_credit=None,
    result_duration=DEFAULT_RESULT_DURATION,
):
    result_files = media_files(results_dir)

    for garment_path in image_files(garments_dir):
        garment_label = label_from_name(garment_path.stem)
        clips.append(
            make_clip(
                garment_path,
                result_duration,
                garment_label,
                tmp_dir,
                description=original_image_description,
                credit=original_image_credit,
            )
        )

        for result_file in result_files:
            if result_file.name.startswith(garment_path.stem + "__"):
                clips.append(make_clip(result_file, result_duration, garment_label, tmp_dir))


def build_reel(
    intro_image,
    results_dir,
    output_file,
    garments_dir=None,
    featured_image=None,
    featured_video=None,
    intro_features=False,
    intro_voiceover=DEFAULT_INTRO_VOICEOVER,
    mascot_image=DEFAULT_MASCOT_IMAGE,
    music_file=DEFAULT_AUDIO,
    end_card=DEFAULT_END_CARD,
    original_image_description=None,
    original_image_credit=None,
    body_type_intro=False,
    result_name_labels=False,
    intro_duration=DEFAULT_INTRO_DURATION,
    result_duration=DEFAULT_RESULT_DURATION,
    end_card_duration=DEFAULT_END_CARD_DURATION,
):
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = output_file.parent / ".reel_labels"
    clips = []

    featured_mode = bool(featured_image or featured_video)
    audio_intro_mode = intro_features
    mascot_path = resolve_image_file(mascot_image) if (featured_mode or intro_features) else None

    if featured_mode:
        clips.append(
            make_clip(
                intro_image,
                intro_duration,
                label_from_name(Path(intro_image).stem),
                tmp_dir,
                mascot_path,
                original_image_description,
                original_image_credit,
            )
        )

        if featured_image:
            clips.append(make_clip(featured_image, result_duration))

        if featured_video:
            clips.append(
                make_clip(featured_video, 1.0).with_effects(
                    [vfx.MultiplySpeed(FEATURED_VIDEO_SPEED)]
                )
            )
    elif garments_dir:
        add_grouped_garment_clips(
            clips,
            garments_dir,
            results_dir,
            tmp_dir,
            original_image_description,
            original_image_credit,
            result_duration,
        )
    else:
        add_flat_result_clips(
            clips,
            intro_image,
            results_dir,
            tmp_dir,
            intro_features=intro_features,
            mascot_path=mascot_path,
            original_image_description=original_image_description,
            original_image_credit=original_image_credit,
            original_image_text_layout=TEXT_LAYOUT_BODY_TYPE if body_type_intro else TEXT_LAYOUT_DEFAULT,
            result_name_labels=result_name_labels,
            intro_duration=intro_duration,
            result_duration=result_duration,
        )

    if Path(end_card).is_file():
        clips.append(make_clip(end_card, end_card_duration))

    if not clips:
        raise RuntimeError("No clips found to build reel")

    video = concatenate_videoclips(clips, method="compose").resized(
        (VIDEO_WIDTH, VIDEO_HEIGHT)
    )

    music_path = resolve_audio_file(music_file)
    intro_voiceover_path = resolve_audio_file(intro_voiceover)

    if music_path or (audio_intro_mode and intro_voiceover_path):
        audio_clips = []
        music_start = intro_duration if audio_intro_mode else 0

        if audio_intro_mode and intro_voiceover_path:
            voiceover = AudioFileClip(str(intro_voiceover_path))
            voiceover_duration = min(voiceover.duration, intro_duration)
            audio_clips.append(voiceover.subclipped(0, voiceover_duration))

        if music_path:
            music_duration = max(video.duration - music_start, 0)
            if music_duration > 0:
                audio = AudioFileClip(str(music_path))
                audio = audio.with_effects([afx.AudioLoop(duration=music_duration)])
                audio_clips.append(audio.subclipped(0, music_duration).with_start(music_start))

        if audio_clips:
            video = video.with_audio(CompositeAudioClip(audio_clips))

    video.write_videofile(
        str(output_file),
        fps=30,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile=str(output_file.with_suffix(".temp-audio.m4a")),
        remove_temp=True,
    )
    return output_file
