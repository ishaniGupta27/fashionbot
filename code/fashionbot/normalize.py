import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, UnidentifiedImageError


TARGET_W = 1080
TARGET_H = 1920
FOOT_Y = 1750


def open_image(input_path):
    input_path = str(input_path)

    try:
        return Image.open(input_path).convert("RGB")
    except UnidentifiedImageError as original_error:
        if not shutil.which("sips"):
            raise original_error

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
            converted_path = tmp_file.name

        try:
            subprocess.run(
                ["sips", "-s", "format", "jpeg", input_path, "--out", converted_path],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return Image.open(converted_path).convert("RGB")
        except Exception:
            raise original_error
        finally:
            if os.path.exists(converted_path):
                os.remove(converted_path)


def normalize_image(input_path, output_path):
    input_path = Path(input_path)
    output_path = Path(output_path)
    img = open_image(input_path)

    scale = TARGET_H / img.height * 0.92
    new_w = int(img.width * scale)
    new_h = int(img.height * scale)
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    canvas = Image.new("RGB", (TARGET_W, TARGET_H), (128, 128, 128))
    x = (TARGET_W - new_w) // 2
    y = FOOT_Y - new_h
    canvas.paste(img, (x, y))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)
    return output_path

