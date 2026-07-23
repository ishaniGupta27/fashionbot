# Fashionbot

Fashionbot turns garment and body-reference images into vertical fashion reels.
The pipeline is job-based: each run has one folder under `jobs/`, and the CLI
only needs the job id.

```bash
cd /Users/Himanshu/Documents/fashionbot/code
venv/bin/python -m fashionbot.run sample_one_body_multiple_garments
```

Use `--dry-run` to validate structure, normalize images, create mock VTO/video
outputs, and build a reel without calling fal.ai:

```bash
venv/bin/python -m fashionbot.run sample_one_body_multiple_garments --dry-run
```

Use `--remote` when the job, archetypes, and assets should be copied from a
remote storage root before the run, and the full job folder should be copied
back after the run:

```bash
venv/bin/python -m fashionbot.run 66 --remote --remote-root gdrive:Fashionbot
```

Remote mode uses `rclone copy`. Local mode never downloads from remote storage
and never uploads anything.

## Core Contract

Three root folders are configured globally:

```text
FASHIONBOT_JOBS_DIR                    defaults to /Users/Himanshu/Documents/fashionbot/jobs
FASHIONBOT_ARCHETYPES_DIR              defaults to /Users/Himanshu/Documents/fashionbot/archetypes
FASHIONBOT_ARCHETYPE_METADATA_DIR      defaults to /Users/Himanshu/Documents/fashionbot/archetype_metadata
```

Each job lives here:

```text
jobs/
  69/
    job.json
    inputs/
    outputs/
    logs/
    status.json
```

`jobs/` is runtime state and is not tracked in Git. In remote mode, jobs are
copied from and back to remote storage.

Lightweight example configs live in:

```text
job_templates/
  one_body_multiple_garments/
    job.json
    inputs/
      original.jpg
      garments/
  one_garment_multiple_bodies/
    job.json
    inputs/
      garment.jpg
  multiple_garments_multiple_bodies/
    job.json
    inputs/
      garments/
  video/
    job.json
    inputs/
      garment.jpg
```

The code resolves all job input paths relative to the job folder. Archetypes are
shared centrally and selected by id through:

```text
archetype_metadata/catalog.json
```

Git-tracked archetype metadata lives under:

```text
archetype_metadata/
  catalog.json
  *.json
```

Heavy archetype images live under `archetypes/` and are intended to come from
remote storage, not Git.

Shared reusable media lives under `assets/` and is also intended to come from
remote storage:

```text
assets/
  audio/
    Jazz.mp3
    voiceover_intro.mp3
  reel/
    end.jpg
    mascot.jpg
  youtube/
    banner.png
    pic.png
```

## Remote Mode

Remote mode is an explicit orchestration path. It is intended for GitHub Actions
or any machine where Google Drive is the source of truth.

Remote storage should mirror the same top-level structure:

```text
Fashionbot/
  assets/
  archetypes/
    final/
    body_types/
  jobs/
    66/
      job.json
      inputs/
      outputs/
      logs/
      status.json
```

Git should not store the remote `jobs/` folder. Git stores only reusable job
templates under `job_templates/`.

Run:

```bash
cd /Users/Himanshu/Documents/fashionbot/code
venv/bin/python -m fashionbot.run 66 --remote --remote-root gdrive:Fashionbot
```

Equivalent environment variable:

```bash
export FASHIONBOT_REMOTE_ROOT="gdrive:Fashionbot"
venv/bin/python -m fashionbot.run 66 --remote
```

Remote mode does this:

```text
1. Copy remote assets/ to local assets/
2. Copy remote archetypes/ to local archetypes/
3. Copy remote jobs/<job_id>/ to local jobs/<job_id>/
4. Run Fashionbot
5. Copy local jobs/<job_id>/ back to remote jobs/<job_id>/
```

Remote mode does not copy `archetype_metadata/` from remote storage. Metadata is
lightweight and lives in Git.

The full job folder is copied both ways so reruns can reuse existing files in
`outputs/vto/` and skip VTO calls that are already done.

Remote job copy excludes `outputs/normalized/` because normalized images are
cheap to regenerate. Remote copy also excludes `.DS_Store` files.

Required remote setup:

```text
rclone installed
rclone remote configured, for example gdrive
FASHIONBOT_REMOTE_ROOT or --remote-root
FAL_KEY for real fal.ai calls
```

Optional:

```text
FASHIONBOT_RCLONE_BIN=/full/path/to/rclone
```

## GitHub Actions

The workflow lives at:

```text
.github/workflows/run-fashionbot.yml
```

It is manually triggered from the GitHub Actions tab and accepts:

```text
job_id
remote_root
execution_mode
generate_metadata
publish_youtube
```

Use this first:

```text
job_id: 2
remote_root: gdrive:fashionbot
execution_mode: dry_run
```

Use `execution_mode: real` when you want fal.ai calls.

Required GitHub repository secrets:

```text
RCLONE_CONFIG
FAL_KEY
OPENAI_API_KEY
YOUTUBE_CLIENT_ID
YOUTUBE_CLIENT_SECRET
YOUTUBE_REFRESH_TOKEN
```

`RCLONE_CONFIG` should be the full contents of:

```text
~/.config/rclone/rclone.conf
```

The workflow runs granular steps:

```text
checkout repo
show inputs
set up Python
install ffmpeg and rclone
install Python dependencies
verify Fashionbot imports
write rclone config from secret
verify FAL_KEY for real runs
verify OPENAI_API_KEY when metadata is enabled
verify YouTube secrets when publish is enabled
check remote root/assets/archetypes/job
run Fashionbot remote dry-run or real job
generate YouTube Shorts metadata when enabled
upload private YouTube Short when enabled
push job folder back to Drive after metadata/publish
show local status
show local output tree
show remote job tree
write GitHub summary
upload short-lived artifact backup
```

## Secrets

For local runs, secrets can be stored in:

```text
secrets/fashionbot.secrets.json
```

That file is ignored by Git. Use this committed example as the shape:

```text
secrets/fashionbot.secrets.example.json
```

The code reads the JSON file first. If a key is blank or missing, it falls back
to the environment variable with the same name.

```json
{
  "FAL_KEY": "",
  "RCLONE_CONFIG": "",
  "OPENAI_API_KEY": "",
  "YOUTUBE_CLIENT_ID": "",
  "YOUTUBE_CLIENT_SECRET": "",
  "YOUTUBE_REFRESH_TOKEN": ""
}
```

## YouTube Shorts Publishing

Publishing is optional and is controlled by GitHub Actions flags. The generation
pipeline stays unchanged.

Add these sections to `job.json`:

```json
"metadata": {
  "brand": "EveryBodyStyledOfficial",
  "handle": "@everybodystyledofficial",
  "theme": "date night looks",
  "audience": "women looking for realistic outfit inspiration across body types",
  "brand_voice": "warm, inclusive, confident, body-positive, stylish",
  "extra_notes": [
    "same body, multiple outfits",
    "ask viewers which look matches their personality"
  ]
},
"youtube": {
  "enabled": true,
  "upload_type": "short",
  "privacy_status": "private",
  "auto_generate_metadata": true,
  "category_id": "26",
  "made_for_kids": false,
  "contains_synthetic_media": true,
  "title": "",
  "description": [],
  "tags": []
}
```

Commands:

```bash
cd /Users/Himanshu/Documents/fashionbot/code
venv/bin/python -m fashionbot.metadata 69
venv/bin/python -m fashionbot.publish 69
```

Metadata is saved to:

```text
jobs/<job_id>/outputs/youtube_metadata.json
```

Upload result is saved to:

```text
jobs/<job_id>/outputs/youtube_upload.json
```

Metadata and publish command logs are saved in:

```text
jobs/<job_id>/logs/
```

The publisher only uploads private Shorts. It refuses to upload unless the reel
is an `.mp4`, exactly `1080x1920`, and `60` seconds or shorter.

## Submit Tool

For a known good laptop, a local curated job folder can be uploaded to Google
Drive and submitted to GitHub Actions with:

```bash
python tools/submit_job.py \
  --job-folder /path/to/2 \
  --creds ~/fashionbot_submit_creds.json
```

The folder name must be numeric. `/path/to/2` becomes job id `2`.

The submit tool uses Google Drive API for upload and GitHub API for workflow
dispatch, so it does not require `rclone` or `gh` on the submit machine. See:

```text
tools/README.md
tools/submit_job.example.json
```

## Modes

Fashionbot supports four modes.

### one_garment_multiple_bodies

One garment is shown on multiple known archetype/body models.

```text
jobs/66/
  job.json
  inputs/
    garment.jpg
```

```json
{
  "mode": "one_garment_multiple_bodies",
  "inputs": {
    "garment_image": "inputs/garment.jpg"
  },
  "models": {
    "archetype_ids": ["1", "13", "34"]
  },
  "vto": {
    "model": "flux",
    "prompt": [
      "virtual try on.",
      "show the garment naturally fitted on the model.",
      "preserve realistic fabric, lighting, proportions, and full outfit detail."
    ],
    "append_garment_name_to_prompt": false
  },
  "reel": {
    "original_image_description": "Original garment",
    "original_image_credit": "",
    "intro_duration": 1.8,
    "result_duration": 1.0,
    "end_card_duration": 1.0
  }
}
```

Output:

```text
outputs/
  normalized/garment.jpg
  vto/1.jpg
  vto/13.jpg
  vto/34.jpg
  reel.mp4
```

### multiple_garments_multiple_bodies

Batch mode. Multiple garments are each shown on multiple known archetype/body
models.

```text
jobs/67/
  job.json
  inputs/
    garments/
      dress_1.jpg
      dress_2.jpg
```

```json
{
  "mode": "multiple_garments_multiple_bodies",
  "inputs": {
    "garments_dir": "inputs/garments"
  },
  "models": {
    "archetype_ids": ["1", "13"]
  },
  "vto": {
    "model": "flux",
    "prompt": [
      "virtual try on.",
      "show each garment naturally fitted on the model."
    ],
    "append_garment_name_to_prompt": true
  },
  "reel": {
    "original_image_description": "Original garment",
    "intro_duration": 1.8,
    "result_duration": 1.0,
    "end_card_duration": 1.0
  }
}
```

Output:

```text
outputs/
  normalized/garments/*.jpg
  vto/dress_1__1.jpg
  vto/dress_1__13.jpg
  reel.mp4
```

### video

One garment plus one known archetype/body model. Fashionbot creates one VTO
image, one generated video, and one reel.

```text
jobs/68/
  job.json
  inputs/
    garment.jpg
```

```json
{
  "mode": "video",
  "inputs": {
    "garment_image": "inputs/garment.jpg"
  },
  "models": {
    "archetype_id": "13"
  },
  "vto": {
    "model": "flux",
    "prompt": ["virtual try on."]
  },
  "video": {
    "prompt": [
      "subtle fashion editorial movement.",
      "natural camera motion.",
      "preserve the outfit and model likeness."
    ],
    "duration": "5",
    "generate_audio": false
  },
  "reel": {
    "original_image_description": "Original garment",
    "intro_duration": 1.8,
    "result_duration": 1.0,
    "end_card_duration": 1.0
  }
}
```

Output:

```text
outputs/
  normalized/garment.jpg
  vto/tryon.jpg
  video/tryon.mp4
  reel.mp4
```

### one_body_multiple_garments

One known archetype/body model and multiple new garment images. An optional
original body/reference image can introduce the reel; if omitted, Fashionbot
uses the selected archetype image as the intro image.

```text
jobs/69/
  job.json
  inputs/
    garments/
      slim-jeans.jpg
      wide-jeans.jpg
```

```json
{
  "mode": "one_body_multiple_garments",
  "inputs": {
    "garments_dir": "inputs/garments"
  },
  "models": {
    "archetype_id": "66"
  },
  "vto": {
    "model": "flux",
    "prompt": [
      "virtual try on.",
      "keep the same body type, face, hair, and overall likeness from the model image.",
      "change pose slightly for movement.",
      "show each garment naturally fitted on the body.",
      "preserve realistic fabric, proportions, lighting, and full outfit detail."
    ],
    "append_garment_name_to_prompt": true
  },
  "reel": {
    "original_image_description": "Body type inspiration",
    "original_image_credit": "",
    "intro_duration": 2.1,
    "result_duration": 1.5,
    "end_card_duration": 1.5,
    "show_result_name_labels": true
  }
}
```

Output:

```text
outputs/
  normalized/original.jpg
  normalized/garments/*.jpg
  vto/slim-jeans.jpg
  vto/wide-jeans.jpg
  reel.mp4
```

## Archetype Catalog

Archetype ids are defined centrally:

```json
{
  "1": "final/1.png",
  "13": "final/13.png",
  "66": "body_types/66.jpg"
}
```

Jobs reference ids only:

```json
"models": {
  "archetype_id": "66"
}
```

or:

```json
"models": {
  "archetype_ids": ["1", "13", "34"]
}
```

## fal.ai

Real VTO/video calls require:

```bash
export FAL_KEY='your_key'
```

or:

```text
code/.env
```

```text
FAL_KEY=your_key
```

`--dry-run` never calls fal.ai.

If fal.ai rejects one VTO item because of a content-policy check, multi-image
modes skip that item, continue with the remaining items, and write the skipped
details into `status.json`. Single-output `video` mode treats that as a failed
job because there is no alternate item to continue with.

## Sample Tests

```bash
cd /Users/Himanshu/Documents/fashionbot/code
venv/bin/python -m fashionbot.run sample_one_garment_multiple_bodies --dry-run
venv/bin/python -m fashionbot.run sample_multiple_garments_multiple_bodies --dry-run
venv/bin/python -m fashionbot.run sample_video --dry-run
venv/bin/python -m fashionbot.run sample_one_body_multiple_garments --dry-run
```
