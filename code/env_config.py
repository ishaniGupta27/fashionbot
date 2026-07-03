"""Small environment helpers shared by fal.ai scripts."""

import os


def load_dotenv_if_present():
    """Load simple KEY=VALUE entries from .env without adding a dependency."""
    env_paths = [
        os.path.join(os.path.dirname(__file__), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
    ]

    for env_path in env_paths:
        if not os.path.isfile(env_path):
            continue

        with open(env_path, "r", encoding="utf-8") as env_file:
            for raw_line in env_file:
                line = raw_line.strip()

                if not line or line.startswith("#") or "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip("'\"")

                if key and key not in os.environ:
                    os.environ[key] = value
