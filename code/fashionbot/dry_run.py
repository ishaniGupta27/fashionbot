from pathlib import Path

from PIL import Image, ImageDraw

from .files import display_name, image_files
from .fonts import bold_font
from .settings import VIDEO_HEIGHT, VIDEO_WIDTH


def font(size):
    return bold_font(size)


def draw_centered_text(draw, lines, y, fill=(255, 255, 255)):
    title_font = font(58)
    body_font = font(38)

    for index, line in enumerate(lines):
        active_font = title_font if index == 0 else body_font
        bbox = draw.textbbox((0, 0), line, font=active_font)
        x = (VIDEO_WIDTH - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), line, font=active_font, fill=fill)
        y += (bbox[3] - bbox[1]) + 28


def mock_image(output_path, title, source=None, accent=(42, 44, 54)):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (124, 124, 124))
    overlay = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), accent)
    img = Image.blend(img, overlay, 0.18)

    draw = ImageDraw.Draw(img)
    draw.rectangle(
        (80, 135, VIDEO_WIDTH - 80, VIDEO_HEIGHT - 135),
        outline=(245, 245, 245),
        width=5,
    )
    draw_centered_text(
        draw,
        [
            title,
            f"source: {display_name(source)}" if source else "dry run placeholder",
        ],
        VIDEO_HEIGHT // 2 - 80,
    )

    img.save(output_path, quality=92)
    return output_path


def mock_vto_for_models(garment_path, model_paths, output_dir):
    output_dir = Path(output_dir)
    outputs = []

    for model_path in model_paths:
        output_path = output_dir / f"{Path(model_path).stem}.jpg"
        outputs.append(
            mock_image(
                output_path,
                f"VTO mock: model {Path(model_path).stem}",
                garment_path,
                accent=(36, 58, 64),
            )
        )

    return outputs


def mock_vto_for_garments(garments_dir, output_dir):
    output_dir = Path(output_dir)
    outputs = []

    for garment_path in image_files(garments_dir):
        output_path = output_dir / f"{garment_path.stem}.jpg"
        outputs.append(
            mock_image(
                output_path,
                f"VTO mock: {display_name(garment_path)}",
                garment_path,
                accent=(66, 50, 42),
            )
        )

    return outputs


def mock_vto_grid(garments_dir, model_paths, output_dir):
    output_dir = Path(output_dir)
    outputs = []

    for garment_path in image_files(garments_dir):
        for model_path in model_paths:
            output_path = output_dir / f"{garment_path.stem}__{Path(model_path).stem}.jpg"
            outputs.append(
                mock_image(
                    output_path,
                    f"{display_name(garment_path)} x {Path(model_path).stem}",
                    garment_path,
                    accent=(48, 52, 72),
                )
            )

    return outputs


def mock_video(source_image, output_path, duration=3):
    from moviepy import ImageClip

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame = mock_image(
        output_path.with_suffix(".mock_source.jpg"),
        "Video mock",
        source_image,
        accent=(38, 42, 58),
    )

    clip = ImageClip(str(frame)).with_duration(float(duration))
    clip.write_videofile(
        str(output_path),
        fps=24,
        codec="libx264",
        audio=False,
        temp_audiofile=str(output_path.with_suffix(".temp-audio.m4a")),
        remove_temp=True,
    )
    return output_path
