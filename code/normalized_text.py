from PIL import Image, ImageDraw, ImageFont
import argparse
import os

TARGET_W = 1080
TARGET_H = 1920

FOOT_Y = 1750


def normalize_image(input_path, hook=None):
    img = Image.open(input_path).convert("RGB")

    #
    # Resize subject
    #
    scale = TARGET_H / img.height * 0.92

    new_w = int(img.width * scale)
    new_h = int(img.height * scale)

    img = img.resize(
        (new_w, new_h),
        Image.Resampling.LANCZOS
    )

    #
    # Create background canvas
    #
    canvas = Image.new(
        "RGB",
        (TARGET_W, TARGET_H),
        (128, 128, 128)
    )

    #
    # Center horizontally
    #
    x = (TARGET_W - new_w) // 2

    #
    # Align feet consistently
    #
    y = FOOT_Y - new_h

    canvas.paste(img, (x, y))

    #
    # Optional title
    #
    if hook:

        draw = ImageDraw.Draw(canvas)

        try:
            font = ImageFont.truetype(
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                58
            )
        except:
            font = ImageFont.load_default()

        #
        # Word wrap
        #
        max_width = 900

        words = hook.split()

        lines = []
        current_line = ""

        for word in words:

            test_line = (
                current_line + " " + word
            ).strip()

            bbox = draw.textbbox(
                (0, 0),
                test_line,
                font=font
            )

            width = bbox[2] - bbox[0]

            if width <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        #
        # Draw centered lines
        #
        y_text = 50

        for line in lines:

            bbox = draw.textbbox(
                (0, 0),
                line,
                font=font
            )

            text_width = bbox[2] - bbox[0]

            draw.text(
                (
                    (TARGET_W - text_width) // 2,
                    y_text
                ),
                line,
                fill="white",
                font=font,
                stroke_width=3,
                stroke_fill="black"
            )

            y_text += 70

    #
    # Save
    #
    base, ext = os.path.splitext(
        input_path
    )

    output_path = (
        f"{base}.normalized{ext}"
    )

    canvas.save(output_path)

    print(f"\n✅ Saved:")
    print(output_path)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        required=True,
        help="Input image"
    )

    parser.add_argument(
        "--hook",
        required=False,
        default=None,
        help="Optional title text"
    )

    args = parser.parse_args()

    normalize_image(
        args.input,
        args.hook
    )

