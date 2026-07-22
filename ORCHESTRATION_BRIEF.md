# Fashionbot Orchestration Brief

This document is a short context brief for asking other AI assistants or
engineers how to run Fashionbot in a cheap, clean, automated pipeline.

It intentionally keeps the project description simple. The goal is not to
explain every code detail. The goal is to explain what the orchestrator needs to
do.

## What Fashionbot Is

Fashionbot is a Python media-generation pipeline for fashion content.

It takes a job folder containing images and a `job.json`, then creates:

- normalized input images
- virtual try-on images using fal.ai
- optional generated video
- a vertical reel for Instagram Reels, TikTok, or YouTube Shorts

The code is now job-based. Runtime input should be only the job id.

Example:

```bash
cd code
python -m fashionbot.run 66
```

Remote orchestration run:

```bash
cd code
python -m fashionbot.run 66 --remote --remote-root gdrive:Fashionbot
```

Safe test run without fal.ai calls:

```bash
cd code
python -m fashionbot.run 66 --dry-run
```

## Current Project Shape

The repo has three main shared roots:

```text
jobs/
  <job_id>/
    job.json
    inputs/
    outputs/
    logs/
    status.json

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

archetypes/
  final/
  body_types/

archetype_metadata/
  catalog.json
  *.json

assets/
  audio/
  reel/
  youtube/
```

The job folder contains new per-job inputs.

`jobs/` is runtime state and should live locally or in remote storage. It is not
part of the Git source of truth. `job_templates/` contains lightweight example
configs that stay in Git.

The archetype folder contains reusable model/body images. Those images are
selected by id from `archetype_metadata/catalog.json`.

`archetype_metadata/` is lightweight and belongs in Git. `archetypes/` and
`assets/` are heavy media folders and belong in remote storage.

The assets folder contains reusable media like audio, end cards, mascot images,
and YouTube assets.

## Supported Job Modes

Fashionbot currently supports four modes:

```text
one_garment_multiple_bodies
multiple_garments_multiple_bodies
video
one_body_multiple_garments
```

The most important modes right now are:

- `one_garment_multiple_bodies`: one garment shown on many archetype/body models
- `one_body_multiple_garments`: one body type/persona shown wearing many garments
- `video`: one garment plus one archetype, then video and reel generation

## What The Orchestrator Must Do

The orchestrator does not need to understand fashion logic deeply. It only needs
to run jobs reliably.

Minimum responsibilities:

- receive or choose a `job_id`
- download the full `jobs/<job_id>/` folder from remote storage
- make sure `jobs/<job_id>/job.json` exists
- make sure job input images exist under `jobs/<job_id>/inputs/`
- keep any existing `jobs/<job_id>/outputs/` files so reruns can resume
- make sure remote `archetypes/` and `assets/` are available on the runner
- make sure Git-tracked `archetype_metadata/` is available in the checkout
- install Python dependencies
- install or provide `ffmpeg`
- set secrets such as `FAL_KEY`
- run `python -m fashionbot.run <job_id>`
- save `jobs/<job_id>/outputs/`, `logs/`, and `status.json`
- upload the full updated `jobs/<job_id>/` folder back to remote storage

Important:

Do not download only `inputs/`. Rerun/resume behavior depends on existing files
inside `outputs/`, especially `outputs/vto/`.

Optional responsibilities:

- fetch job folders from Google Drive, S3, Dropbox, or another remote storage
- upload outputs back to the same remote storage
- run on a schedule
- run manually from a button
- retry failed jobs
- prevent accidental expensive fal.ai runs
- send a Slack/email/notification when done

## Runtime Requirements

The runner needs:

- Python 3.9 or newer
- `pip`
- project Python dependencies
- `ffmpeg`
- outbound internet access
- access to fal.ai
- `FAL_KEY` for real generation
- enough disk space for images, temporary files, and reels
- persistent storage for results after the job finishes

Important note:

Hosted CI runners usually start from a clean machine every run. The repo should
therefore include a `requirements.txt` or similar install file before using a
hosted pipeline.

## Environment Variables

Useful environment variables:

```text
FAL_KEY
FASHIONBOT_JOBS_DIR
FASHIONBOT_ARCHETYPES_DIR
FASHIONBOT_ARCHETYPE_METADATA_DIR
FASHIONBOT_REMOTE_ROOT
FASHIONBOT_RCLONE_BIN
```

`FAL_KEY` is required for real fal.ai generation.

The jobs and archetypes variables are useful if the pipeline downloads inputs
to a different path than the default local repo structure.

`FASHIONBOT_REMOTE_ROOT` is used only with `--remote`. Example:

```text
gdrive:Fashionbot
```

## Cheapest Orchestration Options

### Option 1: GitHub Actions Hosted Runner

This is the cleanest cheap/free starting point.

How it works:

- code stays in GitHub
- workflow is triggered manually with a `job_id`
- GitHub provides a temporary Linux runner
- runner installs dependencies
- runner runs Fashionbot
- outputs are uploaded as GitHub Actions artifacts or pushed to remote storage

Best for:

- occasional real jobs
- occasional small jobs
- proof of automation
- avoiding always-on hardware

Weaknesses:

- hosted runners are temporary
- artifacts/storage have free-tier limits
- large media files may not fit well in GitHub
- archetypes/assets must be downloaded during the run or already cached on the runner
- real VTO jobs may consume fal.ai money quickly if triggered carelessly

Recommendation:

Start here for basic orchestration. Use full-folder Drive sync so existing VTO
outputs are downloaded before reruns and expensive fal.ai calls are skipped when
possible.

### Option 2: GitHub Actions Self-Hosted Runner

This is the cleanest production-ish option if there is any machine available.

The machine does not have to be a Mac mini. It can be:

- a cheap Linux VPS
- an old laptop
- a desktop
- a small cloud VM
- a container host

How it works:

- GitHub Actions remains the orchestrator UI
- the job actually runs on your own machine
- the machine keeps dependencies, archetypes, assets, and cache locally

Best for:

- reliable repeated runs
- larger media jobs
- persistent folders
- easier Google Drive sync
- less setup time per job

Weaknesses:

- you still maintain a machine
- the runner environment is not automatically clean every run
- secrets and local files must be managed carefully

Recommendation:

Use this when hosted runners become annoying because of file size, setup time,
or artifact limits.

### Option 3: GitLab CI Free Hosted Runner

This is similar to GitHub Actions hosted runners.

Best for:

- trying another CI provider
- simple scheduled/manual pipelines

Weaknesses:

- smaller free compute quota than GitHub Free
- requires moving or mirroring the repo to GitLab
- same hosted-runner limitations around large media and temporary storage

Recommendation:

Good backup option, but not the first choice if the code already lives on
GitHub.

### Option 4: Google Colab

This can be nearly free for manual experiments.

Best for:

- experimental runs
- debugging media generation
- one-off notebooks

Weaknesses:

- not a reliable unattended orchestrator
- runtimes are temporary
- free resources are not guaranteed
- not ideal for cron-style jobs

Recommendation:

Useful for testing ideas, not for the main pipeline.

### Option 5: Cheap VPS Plus Cron

This is simple and practical.

How it works:

- rent or use a very cheap Linux server
- clone the repo
- install dependencies once
- run a cron job or small scheduler script
- sync jobs and outputs with Google Drive or another storage service

Best for:

- simple automation
- low ongoing cost
- full control

Weaknesses:

- less polished UI than GitHub Actions
- server maintenance is your responsibility
- needs careful logging and retry behavior

Recommendation:

Good if you want cheap always-on execution without depending on a home machine.

### Option 6: Prefect, n8n, Or Dagster

These are orchestrator/control-plane tools.

Best for:

- cleaner job dashboards
- retries
- schedules
- future multi-step workflows
- connecting Google Drive, notifications, and job queues

Weaknesses:

- still need a worker machine somewhere
- more moving pieces than a simple GitHub Action

Recommendation:

Use later if the workflow grows beyond a simple one-command job runner.

## Not Recommended First

Fully serverless functions are probably not the best first choice.

Reasons:

- video generation needs file handling
- `ffmpeg` can be awkward in serverless
- jobs may run longer than function limits
- media files can be large
- debugging is harder

Serverless can work later for small control tasks, such as receiving a webhook
or enqueueing a job, but it is not ideal as the main media runner.

## Suggested First Pipeline

Use GitHub Actions with a manual trigger.

The checked-in workflow is:

```text
.github/workflows/run-fashionbot.yml
```

The workflow accepts:

```text
job_id
remote_root
execution_mode
```

The routine pipeline should run the real job. The cost guardrail comes from
resume behavior: if a VTO output already exists, Fashionbot skips that fal.ai
call.

Before running the Python command, the workflow should download the full job
folder from Google Drive:

```text
Google Drive/Fashionbot/jobs/<job_id> -> repo jobs/<job_id>
```

After running, it should upload the full updated job folder back:

```text
repo jobs/<job_id> -> Google Drive/Fashionbot/jobs/<job_id>
```

This preserves:

- generated VTO images
- generated videos
- final reel
- status file
- timestamped run logs

Remote job copy should not preserve cheap generated cache such as
`outputs/normalized/`. Those files can be regenerated locally on the next run.

The workflow is intentionally granular. It checks out the repo, installs Python,
installs `ffmpeg` and `rclone`, installs dependencies, verifies imports,
recreates `rclone.conf` from a GitHub secret, checks remote folders, runs
Fashionbot, prints local and remote output trees, writes a GitHub summary, and
uploads a short-lived artifact backup.

The workflow assumes:

- `requirements.txt` exists at the repo root
- `RCLONE_CONFIG` is configured as a GitHub secret
- `FAL_KEY` is configured as a GitHub secret for real runs
- outputs are small enough if you also keep a GitHub artifact copy
- Google Drive is the permanent source of truth

## Google Drive Input And Output

If Google Drive is the remote source of truth, the orchestrator needs extra
steps:

```text
1. Download jobs/<job_id>/ from Google Drive
2. Download or mount remote archetypes/ and assets/
3. Run Fashionbot
4. Upload the full updated jobs/<job_id>/ folder back to Google Drive
```

For a hosted runner, download the full job folder every run.

For a self-hosted runner or VPS, keep heavy archetypes/assets cached locally and
only download the full job folder for the selected job id when appropriate.

## Rerun Behavior

Reruns should be safe and resumable.

Fashionbot already skips VTO/video calls when the expected output file exists.
That means `outputs/vto/` acts like the VTO cache.

Example:

```text
jobs/66/
  outputs/
    vto/
      slim-jeans.jpg
      wide-jeans.jpg
```

If those files are downloaded from Google Drive before the next run, Fashionbot
will see them and skip those VTO calls.

The reel can still be rebuilt from existing outputs. This is useful when text,
timing, labels, audio, or end cards change.

## Logs

Every run should leave a timestamped log file in:

```text
jobs/<job_id>/logs/
```

The Python CLI now prints the log path at startup and tees stdout/stderr into
that file. GitHub Actions still shows live console output, and Google Drive gets
the same audit trail when the full job folder is uploaded back.

## Clean Future Direction

The clean production direction is:

```text
GitHub repo = code, metadata, and job templates
Remote storage = job inputs and generated outputs
Archetype catalog = shared versioned asset set
GitHub Actions = manual trigger and logs
Runner = hosted runner first, self-hosted/VPS later if needed
```

The orchestrator should not need tribal knowledge like:

- where to manually place files outside the job folder
- which script to call for which mode
- which model image path to use
- where final reels appear

It should only need:

```text
job_id
FAL_KEY for real runs
storage credentials if using Google Drive/S3/etc.
```

## Recommended Decision

For the cheapest clean start:

```text
GitHub Actions hosted runner + manual workflow_dispatch + full Google Drive job sync
```

For more reliable repeated generation:

```text
GitHub Actions self-hosted runner on a cheap Linux VPS
```

For the long-term polished system:

```text
GitHub Actions or Prefect as orchestrator
remote storage for jobs/outputs
self-hosted worker for actual media generation
```

## Questions For Another AI Assistant

Good prompts to ask another AI:

```text
Given this project shape, what is the cheapest reliable orchestration design?
```

```text
How should I store and fetch job folders from Google Drive or S3 for this
pipeline?
```

```text
What GitHub Actions workflow should I create for real runs with resumable VTO outputs?
```

```text
Should this use hosted GitHub runners, a self-hosted runner, a VPS, or another
orchestrator?
```

```text
What changes are needed before this repo is ready for hosted CI?
```

## Sources Checked

- GitHub Actions billing and free included minutes:
  https://docs.github.com/en/billing/concepts/product-billing/github-actions
- GitHub self-hosted runners overview:
  https://docs.github.com/en/actions/concepts/runners/self-hosted-runners
- GitHub self-hosted runner requirements:
  https://docs.github.com/en/actions/reference/runners/self-hosted-runners
- GitLab CI compute minutes:
  https://docs.gitlab.com/ci/pipelines/compute_minutes/
- Google Colab FAQ:
  https://research.google.com/colaboratory/faq.html
