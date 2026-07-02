from PIL import Image
import os
import argparse

TARGET_W = 1080
TARGET_H = 1920

# Feet should land here
FOOT_Y = 1750


def normalize_image(input_path, output_path):
    img = Image.open(input_path).convert("RGB")

    # Scale image so person fills most of frame
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

    # Place feet consistently
    y = FOOT_Y - new_h

    canvas.paste(img, (x, y))

    canvas.save(output_path)


def normalize_folder(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    for filename in sorted(os.listdir(input_dir)):
        if not filename.lower().endswith(
            (".png", ".jpg", ".jpeg")
        ):
            continue

        input_path = os.path.join(
            input_dir,
            filename
        )

        output_path = os.path.join(
            output_dir,
            filename
        )

        normalize_image(
            input_path,
            output_path
        )

        print(f"Saved {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        required=True
    )

    parser.add_argument(
        "--output",
        required=True
    )

    args = parser.parse_args()

    normalize_folder(
        args.input,
        args.output
    )

