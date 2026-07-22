from pathlib import Path

from PIL import ImageFont


BOLD_FONT_PATHS = (
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Helvetica Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
)


def bold_font(size):
    for font_path in BOLD_FONT_PATHS:
        if Path(font_path).exists():
            return ImageFont.truetype(font_path, size)

    try:
        return ImageFont.load_default(size=size)
    except TypeError as e:
        raise RuntimeError(
            "No scalable bold font found. Install DejaVu fonts on the runner "
            "or add a valid font path in code/fashionbot/fonts.py."
        ) from e
