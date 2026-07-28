import json
import random
import re

from PIL import Image, ImageDraw, ImageFilter

from .errors import FashionbotError
from .fonts import bold_font
from .openai_response import extract_response_text, parse_json_text
from .secrets import secret_value
from .settings import VIDEO_HEIGHT, VIDEO_WIDTH
from .status import utc_now


DEFAULT_OPENAI_MODEL = "gpt-5-mini"
SPEC_FILE = "intro_slide_spec.json"
SLIDE_FILE = "intro_slide.jpg"
DEFAULT_PALETTE = ["#F4EFE8", "#E7D8CC", "#C9B9A6", "#A98268", "#3A302A"]
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


SYSTEM_PROMPT = """
You design elegant vertical title-slide backgrounds for fashion reels.
Return only valid JSON. Do not wrap it in markdown.

Required JSON shape:
{
  "palette": ["#hex", "#hex", "#hex", "#hex", "#hex"],
  "text_color": "#hex",
  "accent_color": "#hex",
  "background_style": "short phrase",
  "mood_words": ["word", "word", "word"]
}

Rules:
- Palette must feel soft, feminine, quiet luxury, wearable, and low saturation.
- Avoid neon, loud contrast, bright saturated colors, and busy patterns.
- Prefer ivory, blush, taupe, champagne, muted sage, dusty rose, camel, pearl.
- Text color must have strong readability on the palette.
- Return exactly 5 palette colors.
""".strip()


def intro_slide_config(job):
    config = job.config.get("intro_slide", {})
    if not isinstance(config, dict):
        raise FashionbotError("intro_slide must be an object when provided")
    return config


def enabled(job):
    return bool(intro_slide_config(job).get("enabled", False))


def output_path(job):
    return job.outputs_dir / SLIDE_FILE


def spec_path(job):
    return job.outputs_dir / SPEC_FILE


def hex_to_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def valid_hex(value):
    return isinstance(value, str) and bool(HEX_RE.match(value))


def clean_spec(payload):
    if not isinstance(payload, dict):
        raise FashionbotError("Intro slide spec must be a JSON object")

    palette = payload.get("palette")
    if not isinstance(palette, list):
        palette = []

    colors = [color for color in palette if valid_hex(color)]
    if len(colors) < 5:
        colors = DEFAULT_PALETTE
    else:
        colors = colors[:5]

    text_color = payload.get("text_color")
    accent_color = payload.get("accent_color")

    return {
        "palette": colors,
        "text_color": text_color if valid_hex(text_color) else colors[-1],
        "accent_color": accent_color if valid_hex(accent_color) else colors[3],
        "background_style": str(payload.get("background_style", "soft editorial gradient"))[:140],
        "mood_words": [
            str(word)[:40]
            for word in payload.get("mood_words", [])
            if isinstance(word, str) and word.strip()
        ][:6],
    }


def metadata_context(job):
    metadata = job.config.get("metadata", {})
    intro = intro_slide_config(job)
    if not isinstance(metadata, dict):
        raise FashionbotError("metadata must be an object when provided")

    return {
        "brand": metadata.get("brand", "EveryBodyStyledOfficial"),
        "handle": metadata.get("handle", "@everybodystyledofficial"),
        "theme": metadata.get("theme", ""),
        "audience": metadata.get("audience", ""),
        "brand_voice": metadata.get("brand_voice", ""),
        "extra_notes": metadata.get("extra_notes", []),
        "style_notes": intro.get("style_notes", []),
        "title": intro.get("title", ""),
        "subtitle": intro.get("subtitle", ""),
    }


def call_openai_for_spec(job):
    import requests

    api_key = secret_value("OPENAI_API_KEY", required=True)
    model = intro_slide_config(job).get("model") or secret_value("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL
    context = metadata_context(job)

    print("Generating intro slide background spec with OpenAI")
    print(f"OpenAI model: {model}")
    print(f"Intro theme: {context['theme'] or '(not provided)'}")

    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "input": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Create the background design spec from this context:\n"
                        + json.dumps(context, indent=2)
                    ),
                },
            ],
            "max_output_tokens": 500,
        },
        timeout=90,
    )

    if response.status_code >= 400:
        raise FashionbotError(
            f"OpenAI intro slide request failed: HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )

    text = extract_response_text(response.json(), label="OpenAI intro slide response")
    return clean_spec(parse_json_text(text, label="OpenAI intro slide"))


def fallback_spec(job):
    return {
        "palette": DEFAULT_PALETTE,
        "text_color": "#342B26",
        "accent_color": "#A98268",
        "background_style": "soft quiet luxury gradient",
        "mood_words": ["soft", "feminine", "timeless"],
    }


def vertical_gradient(top, bottom):
    image = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), top)
    draw = ImageDraw.Draw(image)
    for y in range(VIDEO_HEIGHT):
        ratio = y / max(VIDEO_HEIGHT - 1, 1)
        color = tuple(int(top[i] * (1 - ratio) + bottom[i] * ratio) for i in range(3))
        draw.line((0, y, VIDEO_WIDTH, y), fill=color)
    return image


def add_soft_shapes(image, colors):
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    rng = random.Random("|".join(colors))

    for index in range(9):
        color = hex_to_rgb(colors[index % len(colors)])
        alpha = rng.randint(28, 54)
        width = rng.randint(360, 760)
        height = rng.randint(280, 620)
        x = rng.randint(-180, VIDEO_WIDTH - 180)
        y = rng.randint(-120, VIDEO_HEIGHT - 120)
        draw.ellipse((x, y, x + width, y + height), fill=(*color, alpha))

    overlay = overlay.filter(ImageFilter.GaussianBlur(70))
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def add_paper_texture(image):
    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    rng = random.Random("fashionbot-intro-texture")

    for _ in range(1800):
        x = rng.randrange(VIDEO_WIDTH)
        y = rng.randrange(VIDEO_HEIGHT)
        alpha = rng.randrange(4, 12)
        draw.point((x, y), fill=(255, 255, 255, alpha))

    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def wrap_lines(draw, text, font, max_width):
    words = str(text or "").split()
    lines = []
    current = ""

    for word in words:
        candidate = word if not current else f"{current} {word}"
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word

    if current:
        lines.append(current)
    return lines


def draw_centered_lines(draw, lines, font, y, fill, line_gap):
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        draw.text(((VIDEO_WIDTH - width) / 2, y), line, font=font, fill=fill)
        y += height + line_gap
    return y


def render_slide(job, spec):
    intro = intro_slide_config(job)
    title = str(intro.get("title", "")).strip()
    subtitle = str(intro.get("subtitle", "")).strip()

    if not title:
        raise FashionbotError("intro_slide.title is required when intro_slide.enabled is true")

    colors = spec["palette"]
    image = vertical_gradient(hex_to_rgb(colors[0]), hex_to_rgb(colors[1]))
    image = add_soft_shapes(image, colors[1:5])
    image = add_paper_texture(image)

    draw = ImageDraw.Draw(image)
    text_fill = hex_to_rgb(spec["text_color"])
    accent_fill = hex_to_rgb(spec["accent_color"])
    title_font = bold_font(74)
    subtitle_font = bold_font(38)
    handle_font = bold_font(28)

    max_width = int(VIDEO_WIDTH * 0.78)
    title_lines = wrap_lines(draw, title, title_font, max_width)
    subtitle_lines = wrap_lines(draw, subtitle, subtitle_font, max_width) if subtitle else []

    title_height = 0
    for line in title_lines:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        title_height += (bbox[3] - bbox[1]) + 18

    subtitle_height = 0
    for line in subtitle_lines:
        bbox = draw.textbbox((0, 0), line, font=subtitle_font)
        subtitle_height += (bbox[3] - bbox[1]) + 12

    total_height = title_height + subtitle_height + 46
    y = int((VIDEO_HEIGHT - total_height) * 0.44)

    line_width = int(VIDEO_WIDTH * 0.22)
    draw.rounded_rectangle(
        (
            (VIDEO_WIDTH - line_width) / 2,
            y - 48,
            (VIDEO_WIDTH + line_width) / 2,
            y - 42,
        ),
        radius=3,
        fill=accent_fill,
    )

    y = draw_centered_lines(draw, title_lines, title_font, y, text_fill, 18)
    if subtitle_lines:
        y += 28
        draw_centered_lines(draw, subtitle_lines, subtitle_font, y, text_fill, 12)

    handle = metadata_context(job).get("handle") or ""
    if handle:
        bbox = draw.textbbox((0, 0), handle, font=handle_font)
        draw.text(
            ((VIDEO_WIDTH - (bbox[2] - bbox[0])) / 2, VIDEO_HEIGHT - 164),
            handle,
            font=handle_font,
            fill=text_fill,
        )

    return image


def generate_intro_slide(job, dry_run=False):
    intro = intro_slide_config(job)
    if not intro.get("enabled", False):
        return None

    use_openai = not dry_run and intro.get("auto_generate_background", False)
    if use_openai:
        try:
            spec = call_openai_for_spec(job)
        except FashionbotError as e:
            print(f"WARNING: intro slide OpenAI generation failed: {e}")
            print("Using local fallback intro slide background spec")
            spec = fallback_spec(job)
            use_openai = False
    else:
        spec = fallback_spec(job)

    payload = {
        **spec,
        "generated_at": utc_now(),
        "source": "openai" if use_openai else "local_fallback",
    }

    job.outputs_dir.mkdir(parents=True, exist_ok=True)
    with spec_path(job).open("w") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")

    slide = render_slide(job, spec)
    path = output_path(job)
    slide.save(path, quality=95)
    print(f"Intro slide saved: {path}")
    return path
