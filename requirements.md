# Fashionbot Requirements

## Runtime

- macOS or Linux runner
- Python 3.9+
- ffmpeg available to MoviePy
- Python packages already installed in `code/venv`
- `FAL_KEY` for real fal.ai VTO/video generation

Dry-runs do not require `FAL_KEY`.

## Public CLI

Fashionbot has one public command:

```bash
cd /Users/Himanshu/Documents/fashionbot/code
venv/bin/python -m fashionbot.run <job_id>
```

Safe local testing:

```bash
venv/bin/python -m fashionbot.run <job_id> --dry-run
```

The CLI finds:

```text
$FASHIONBOT_JOBS_DIR/<job_id>/job.json
```

If `FASHIONBOT_JOBS_DIR` is not set, it uses:

```text
/Users/Himanshu/Documents/fashionbot/jobs
```

If `FASHIONBOT_ARCHETYPES_DIR` is not set, it uses:

```text
/Users/Himanshu/Documents/fashionbot/archetypes
```

Shared reusable media lives in:

```text
assets/audio/
assets/reel/
assets/youtube/
```

## Job Contract

Each job must contain:

```text
jobs/<job_id>/
  job.json
  inputs/
```

Fashionbot creates:

```text
jobs/<job_id>/
  outputs/
  logs/
  status.json
```

All `inputs.*` paths inside `job.json` must be relative to the job folder.
Archetypes are not copied into jobs. Jobs reference central archetype ids from
`archetypes/catalog.json`.

## Supported Modes

```text
one_garment_multiple_bodies
multiple_garments_multiple_bodies
video
one_body_multiple_garments
```

## Mode Inputs

`one_garment_multiple_bodies`:

```text
inputs/garment.jpg
models.archetype_ids
```

`multiple_garments_multiple_bodies`:

```text
inputs/garments/
models.archetype_ids
```

`video`:

```text
inputs/garment.jpg
models.archetype_id
video.prompt
```

`one_body_multiple_garments`:

```text
inputs/original.jpg
inputs/garments/
models.archetype_id
```

## Status

Each run writes `status.json`:

```json
{
  "job_id": "69",
  "mode": "one_body_multiple_garments",
  "status": "done",
  "updated_at": "2026-07-22T12:00:00+00:00",
  "dry_run": true,
  "outputs": {
    "reel": "/path/to/jobs/69/outputs/reel.mp4"
  }
}
```

Possible status values:

```text
running
done
failed
```
