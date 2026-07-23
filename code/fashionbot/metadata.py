import argparse
import json

from .errors import FashionbotError
from .files import display_name, image_files
from .job import load_job, prompt_text
from .runlog import run_log_path, tee_to_log
from .secrets import secret_value
from .settings import (
    archetype_metadata_dir,
    archetypes_dir,
    jobs_dir,
)
from .status import utc_now


DEFAULT_OPENAI_MODEL = "gpt-5-mini"
OUTPUT_FILE = "youtube_metadata.json"
MAX_TITLE_LENGTH = 100
MAX_TAGS_LENGTH = 500


SYSTEM_PROMPT = """
You create YouTube Shorts metadata for EveryBodyStyledOfficial.
Return only valid JSON. Do not wrap it in markdown.

Required JSON shape:
{
  "title": "one line, max 100 characters",
  "description": ["paragraph line", "", "paragraph line", "", "question", "", "#Shorts"],
  "tags": ["Title Case Tag", "Another Tag"]
}

Style pattern:
- Title should be searchable, warm, and punchy.
- Description should follow this exact rhythm:
  1. Hook about confidence or style.
  2. Blank line.
  3. Specific paragraph about the outfits/theme.
  4. Blank line.
  5. Brand belief paragraph mentioning @everybodystyledofficial.
  6. Blank line.
  7. Viewer question.
  8. Blank line.
  9. #Shorts
- Tags must be clean search phrases, not hashtags.
- Tags total length, joined by comma and space, must be 500 characters or less.
- Do not make fake claims.
- Do not mention AI unless the job asks for it.
""".strip()


def metadata_path(job):
    return job.outputs_dir / OUTPUT_FILE


def description_to_text(description):
    if isinstance(description, list):
        return "\n".join(str(line) for line in description)
    return str(description or "")


def normalize_description(description):
    if isinstance(description, str):
        lines = description.splitlines()
    elif isinstance(description, list) and all(isinstance(item, str) for item in description):
        lines = description
    else:
        raise FashionbotError("metadata.description must be a string or list of strings")

    lines = [line.rstrip() for line in lines]
    if "#Shorts" not in "\n".join(lines):
        if lines and lines[-1] != "":
            lines.append("")
        lines.append("#Shorts")

    return lines


def trim_tags(tags):
    trimmed = []
    for tag in tags:
        candidate = str(tag).strip()
        if not candidate:
            continue

        next_tags = trimmed + [candidate]
        if len(", ".join(next_tags)) > MAX_TAGS_LENGTH:
            break
        trimmed.append(candidate)

    return trimmed


def validate_metadata(payload):
    if not isinstance(payload, dict):
        raise FashionbotError("OpenAI metadata response must be a JSON object")

    title = str(payload.get("title", "")).strip()
    if not title:
        raise FashionbotError("metadata.title is required")
    if len(title) > MAX_TITLE_LENGTH:
        raise FashionbotError(
            f"metadata.title must be {MAX_TITLE_LENGTH} characters or less"
        )

    description = normalize_description(payload.get("description"))
    tags = payload.get("tags")
    if not isinstance(tags, list):
        raise FashionbotError("metadata.tags must be a list")

    tags = trim_tags(tags)
    if not tags:
        raise FashionbotError("metadata.tags must contain at least one tag")

    return {
        "title": title,
        "description": description,
        "tags": tags,
    }


def extract_response_text(response_json):
    if response_json.get("output_text"):
        return response_json["output_text"]

    chunks = []
    for item in response_json.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if text:
                chunks.append(text)

    return "\n".join(chunks).strip()


def parse_json_text(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.startswith("json"):
            text = text[len("json") :].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise FashionbotError(f"OpenAI returned invalid metadata JSON: {e}") from e


def job_garment_names(job):
    inputs = job.config.get("inputs", {})
    names = []

    if inputs.get("garment_image"):
        names.append(display_name(inputs["garment_image"]))

    if inputs.get("garments_dir"):
        garments_dir = job.root / inputs["garments_dir"]
        names.extend(display_name(path) for path in image_files(garments_dir))

    return [name for name in names if name]


def metadata_context(job):
    job_metadata = job.config.get("metadata", {})
    youtube = job.config.get("youtube", {})
    vto = job.config.get("vto", {})

    if not isinstance(job_metadata, dict):
        raise FashionbotError("metadata must be an object when provided")
    if not isinstance(youtube, dict):
        raise FashionbotError("youtube must be an object when provided")

    return {
        "brand": job_metadata.get("brand", "EveryBodyStyledOfficial"),
        "handle": job_metadata.get("handle", "@everybodystyledofficial"),
        "platform": "youtube_shorts",
        "mode": job.mode,
        "theme": job_metadata.get("theme", ""),
        "audience": job_metadata.get("audience", ""),
        "brand_voice": job_metadata.get(
            "brand_voice",
            "warm, inclusive, confident, body-positive, stylish",
        ),
        "extra_notes": job_metadata.get("extra_notes", []),
        "garment_names": job_garment_names(job),
        "vto_prompt": prompt_text(vto.get("prompt"), "vto.prompt"),
        "existing_title": youtube.get("title", ""),
        "existing_description": description_to_text(youtube.get("description", [])),
        "existing_tags": youtube.get("tags", []),
    }


def call_openai(context, model, api_key):
    import requests

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
                        "Create metadata from this job context:\n"
                        + json.dumps(context, indent=2)
                    ),
                },
            ],
        },
        timeout=90,
    )

    if response.status_code >= 400:
        raise FashionbotError(
            f"OpenAI metadata request failed: HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )

    text = extract_response_text(response.json())
    if not text:
        raise FashionbotError("OpenAI metadata response did not contain text")

    return parse_json_text(text)


def generate_metadata(job, model=None, force=False):
    output_path = metadata_path(job)
    if output_path.is_file() and not force:
        print(f"SKIP metadata already exists: {output_path}")
        return output_path

    youtube = job.config.get("youtube", {})
    if not isinstance(youtube, dict) or not youtube.get("enabled", False):
        raise FashionbotError("youtube.enabled must be true to generate metadata")

    if not youtube.get("auto_generate_metadata", False):
        raise FashionbotError("youtube.auto_generate_metadata must be true")

    api_key = secret_value("OPENAI_API_KEY", required=True)
    active_model = model or secret_value("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL
    context = metadata_context(job)

    print("Generating YouTube Shorts metadata with OpenAI")
    print(f"OpenAI model: {active_model}")
    print(f"Job theme: {context['theme'] or '(not provided)'}")
    print(f"Garments: {len(context['garment_names'])}")

    try:
        generated = validate_metadata(call_openai(context, active_model, api_key))
    except FashionbotError as first_error:
        retry_context = dict(context)
        retry_context["previous_error"] = str(first_error)
        print("Metadata validation failed once; retrying with validation feedback")
        generated = validate_metadata(call_openai(retry_context, active_model, api_key))

    payload = {
        **generated,
        "generated_at": utc_now(),
        "source": "openai",
        "model": active_model,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")

    print(f"Metadata saved: {output_path}")
    print(f"Title: {payload['title']}")
    print(f"Tags: {len(payload['tags'])}")
    return output_path


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate YouTube Shorts metadata for a Fashionbot job."
    )
    parser.add_argument("job_id", help="Job folder name under jobs/")
    parser.add_argument("--jobs-dir", default=None, help="Override FASHIONBOT_JOBS_DIR")
    parser.add_argument(
        "--archetypes-dir",
        default=None,
        help="Override FASHIONBOT_ARCHETYPES_DIR",
    )
    parser.add_argument(
        "--archetype-metadata-dir",
        default=None,
        help="Override FASHIONBOT_ARCHETYPE_METADATA_DIR",
    )
    parser.add_argument("--model", default=None, help="Override OPENAI_MODEL")
    parser.add_argument("--force", action="store_true", help="Regenerate metadata")

    args = parser.parse_args(argv)

    active_jobs_dir = args.jobs_dir or jobs_dir()
    log_path = run_log_path(active_jobs_dir, args.job_id, prefix="metadata")

    with tee_to_log(log_path):
        print(f"Metadata log: {log_path}")
        try:
            job = load_job(
                args.job_id,
                active_jobs_dir,
                args.archetypes_dir or archetypes_dir(),
                args.archetype_metadata_dir or archetype_metadata_dir(),
            )
            generate_metadata(job, model=args.model, force=args.force)
        except FashionbotError as e:
            print(f"ERROR: {e}")
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
