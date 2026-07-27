import json

from .errors import FashionbotError


def _collect_text(value, chunks):
    if isinstance(value, str):
        if value.strip():
            chunks.append(value)
        return

    if isinstance(value, list):
        for item in value:
            _collect_text(item, chunks)
        return

    if not isinstance(value, dict):
        return

    value_type = value.get("type")
    if value_type in ("output_text", "text") and isinstance(value.get("text"), str):
        chunks.append(value["text"])
        return

    if isinstance(value.get("output_text"), str):
        chunks.append(value["output_text"])

    for key in ("text", "content", "output"):
        if key in value:
            _collect_text(value[key], chunks)


def extract_response_text(response_json, label="OpenAI response"):
    chunks = []
    _collect_text(response_json, chunks)

    text = "\n".join(chunk.strip() for chunk in chunks if chunk.strip()).strip()
    if text:
        return text

    status = response_json.get("status") if isinstance(response_json, dict) else None
    error = response_json.get("error") if isinstance(response_json, dict) else None
    incomplete = (
        response_json.get("incomplete_details")
        if isinstance(response_json, dict)
        else None
    )

    details = []
    if status:
        details.append(f"status={status}")
    if error:
        details.append(f"error={error}")
    if incomplete:
        details.append(f"incomplete_details={incomplete}")

    suffix = f" ({'; '.join(details)})" if details else ""
    raise FashionbotError(f"{label} did not contain text{suffix}")


def parse_json_text(text, label="OpenAI"):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.startswith("json"):
            text = text[len("json") :].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise FashionbotError(f"{label} returned invalid JSON: {e}") from e
