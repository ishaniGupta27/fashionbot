"""Normalize garment images onto a 1080x1920 gray canvas for reel/VTO use."""

from PIL import Image
import argparse
import os

TARGET_W = 1080
TARGET_H = 1920

FOOT_Y = 1750


def normalize_image(input_path, output_path=None):
    img = Image.open(input_path).convert("RGB")

    scale = TARGET_H / img.height * 0.92

    new_w = int(img.width * scale)
    new_h = int(img.height * scale)

    img = img.resize(
        (new_w, new_h),
        Image.Resampling.LANCZOS
    )

    canvas = Image.new(
        "RGB",
        (TARGET_W, TARGET_H),
        (128, 128, 128)
    )

    x = (TARGET_W - new_w) // 2
    y = FOOT_Y - new_h

    canvas.paste(img, (x, y))

    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}.normalized{ext}"

    os.makedirs(
        os.path.dirname(output_path),
        exist_ok=True
    )

    canvas.save(output_path)

    print(f"Saved: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        required=True,
        help="Input image"
    )

    parser.add_argument(
        "--output",
        default=None,
        help="Output image"
    )

    args = parser.parse_args()

    normalize_image(args.input, args.output)
