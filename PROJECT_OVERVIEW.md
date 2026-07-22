# Fashionbot Project Overview

This document is a high-context brief for sharing Fashionbot with other AI
assistants, collaborators, or future engineers. It explains what the project
does, why it exists, how it is structured, and where it can go next.

## Short Summary

Fashionbot is a local media-generation pipeline for fashion content. It takes
garment images, body/reference images, and reusable archetype model images, then
creates virtual try-on outputs and short vertical reels for Instagram Reels,
TikTok, YouTube Shorts, and similar social formats.

The system is designed around a clean job contract:

```bash
cd /Users/Himanshu/Documents/fashionbot/code
venv/bin/python -m fashionbot.run <job_id>
```

For safe testing without fal.ai calls:

```bash
venv/bin/python -m fashionbot.run <job_id> --dry-run
```

Each job is a self-contained folder under `jobs/<job_id>/`. The only user input
needed at runtime is the job id.

`jobs/` is runtime state and is not part of the Git source of truth. Git keeps
lightweight examples under `job_templates/`.

## Product Idea

Fashionbot helps create fashion discovery content from a small set of inputs.
The core creative question is:

```text
How does this garment look on different bodies?
```

or:

```text
How would multiple garments look on this one body type/persona?
```

The project is especially useful for:

- Short-form fashion videos
- Virtual try-on content
- Body-type-aware outfit discovery
- Product showcase reels
- Celebrity/body-inspiration styling content
- Social commerce experiments
- Fit and styling comparison content

## Current Audience

The most important audience is a fashion/social viewer who wants fast visual
answers:

- “Would this dress work on someone shaped like me?”
- “How do these jeans look on this body type?”
- “Show me this outfit across multiple model archetypes.”
- “Make a premium motion post for this garment.”

The project is also useful for creators/operators who want to generate many
reels without manually managing dozens of image paths.

## Main Modes

Fashionbot currently supports four modes.

### 1. `one_garment_multiple_bodies`

One garment is shown on multiple known archetype/body models.

Use this for product showcase content.

Example:

```text
one white dress -> model 1, model 13, model 34 -> reel
```

Inputs:

```text
jobs/<job_id>/
  job.json
  inputs/
    garment.jpg
```

Model selection:

```json
"models": {
  "archetype_ids": ["1", "13", "34"]
}
```

Outputs:

```text
outputs/
  normalized/garment.jpg
  vto/1.jpg
  vto/13.jpg
  vto/34.jpg
  reel.mp4
```

### 2. `multiple_garments_multiple_bodies`

Multiple garments are each shown on multiple known archetype/body models.

This is batch/catalog mode. It is supported, but it is less central to the
current product direction than modes 1, 3, and 4.

Example:

```text
dress_1, dress_2 -> model 1, model 13 -> grouped reel
```

Inputs:

```text
jobs/<job_id>/
  job.json
  inputs/
    garments/
      dress_1.jpg
      dress_2.jpg
```

Model selection:

```json
"models": {
  "archetype_ids": ["1", "13"]
}
```

Outputs:

```text
outputs/
  normalized/garments/*.jpg
  vto/dress_1__1.jpg
  vto/dress_1__13.jpg
  vto/dress_2__1.jpg
  vto/dress_2__13.jpg
  reel.mp4
```

### 3. `video`

One garment and one archetype/body model produce one VTO image, then one
generated video, then one reel.

Use this for premium posts where motion matters.

Example:

```text
one garment + model 13 -> tryon.jpg -> tryon.mp4 -> reel.mp4
```

Inputs:

```text
jobs/<job_id>/
  job.json
  inputs/
    garment.jpg
```

Model selection:

```json
"models": {
  "archetype_id": "13"
}
```

Outputs:

```text
outputs/
  normalized/garment.jpg
  vto/tryon.jpg
  video/tryon.mp4
  reel.mp4
```

### 4. `one_body_multiple_garments`

One optional body/reference image introduces the reel. If that image is omitted,
the selected archetype/body model introduces the reel. That same archetype/body
model then wears many garments.

This is currently one of the most important modes. It serves viewers who relate
to a body type, celebrity inspiration, or style persona first, then want outfit
ideas for that body.

Example:

```text
optional body reference + body archetype 66
-> baggy jeans, straight jeans, wide-leg jeans
-> reel
```

Inputs:

```text
jobs/<job_id>/
  job.json
  inputs/
    garments/
      baggy-jeans.jpg
      straight-jeans.jpg
      wide-leg-jeans.jpg
```

`inputs.original_image` can be provided for a separate intro/reference image. If
it is missing, Fashionbot falls back to `models.archetype_id`.

Model selection:

```json
"models": {
  "archetype_id": "66"
}
```

Outputs:

```text
outputs/
  normalized/original.jpg
  normalized/garments/*.jpg
  vto/baggy-jeans.jpg
  vto/straight-jeans.jpg
  vto/wide-leg-jeans.jpg
  reel.mp4
```

## Job Folder Contract

Every job lives under:

```text
jobs/<job_id>/
```

Each job contains:

```text
job.json
inputs/
```

Fashionbot creates:

```text
outputs/
logs/
status.json
```

All paths in `job.json` are relative to the job folder.

The project intentionally avoids older hardcoded conventions like:

```text
garments/og/<id>.jpg
code/input/<id>.json
reels/reel_<id>.mp4
```

Those were legacy prototype conventions. The production direction is the job
contract.

## Archetype Model System

Archetypes are reusable known model/body images stored centrally under:

```text
archetypes/
```

This is a heavy media folder. In orchestrated runs it should come from remote
storage.

Jobs do not copy archetype images. Jobs reference archetypes by id.

The lightweight metadata catalog lives at:

```text
archetype_metadata/catalog.json
```

Example:

```json
{
  "1": "final/1.png",
  "13": "final/13.png",
  "34": "final/34.png",
  "66": "body_types/66.jpg"
}
```

Job example:

```json
"models": {
  "archetype_ids": ["1", "13", "34"]
}
```

or:

```json
"models": {
  "archetype_id": "66"
}
```

The code resolves those ids through the catalog.

## Shared Assets

Reusable non-job media lives under:

```text
assets/
  audio/
    Jazz.mp3
    voiceover_intro.mp3
    voiceover_intro_2.mp3
  reel/
    end.jpg
    mascot.jpg
  youtube/
    banner.png
    pic.png
```

These are shared assets for reel building and eventual YouTube/channel work.

## Current Code Structure

The main package lives at:

```text
code/fashionbot/
```

Important modules:

```text
run.py          CLI entrypoint
job.py          job.json validation and schema rules
runner.py       mode orchestration
archetypes.py   archetype id lookup
normalize.py    image normalization
vto.py          fal.ai virtual try-on wrapper
video.py        fal.ai image-to-video wrapper
reel.py         vertical reel builder
dry_run.py      mock VTO/video outputs for safe tests
status.py       status.json writer
settings.py     global paths and defaults
errors.py       clean user-facing errors
```

The intended public entrypoint is:

```bash
venv/bin/python -m fashionbot.run <job_id>
```

## Processing Flow

High-level flow:

```text
1. Load jobs/<job_id>/job.json
2. Validate required inputs for the selected mode
3. Resolve archetype ids through archetype_metadata/catalog.json
4. Normalize garment/body images to 1080x1920 canvas
5. Generate VTO images through fal.ai, unless --dry-run is used
6. Optionally generate video for video mode
7. Build a vertical reel with MoviePy
8. Write outputs and status.json under the job folder
```

## Dry Run

Dry-run is central to the development workflow:

```bash
venv/bin/python -m fashionbot.run sample_one_body_multiple_garments --dry-run
```

Dry-run does:

- Validates `job.json`
- Verifies input files
- Resolves archetype ids
- Normalizes images
- Creates local mock VTO images
- Creates local mock video for `video` mode
- Builds a real `reel.mp4`
- Does not call fal.ai
- Does not require `FAL_KEY`

This lets users test structure and reel behavior without spending money.

## Real Generation

Real VTO/video calls require fal.ai credentials:

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

Then run without `--dry-run`:

```bash
venv/bin/python -m fashionbot.run <job_id>
```

Provider behavior:

- Authentication/key failures stop the job.
- Multi-image VTO modes skip individual items rejected by fal.ai content-policy
  checks and continue with the rest.
- Skipped VTO items are written to `status.json`.
- `video` mode fails on a rejected VTO pair because it only has one source image
  to animate.

## Reel Behavior

All reels are vertical:

```text
1080 x 1920
```

The reel builder supports:

- Original/intro image
- VTO result clips
- Optional video segment
- Optional end card
- Background music
- Intro voiceover/mascot support
- Original image description
- Original image credit
- Garment-name labels for one-body/multiple-garments content

Mode `one_body_multiple_garments` has special presentation behavior:

- Original body/reference image is shown first
- Intro image stays longer by default
- Original image description/credit appears around the 3/4 vertical point
- Generated VTO images can show garment names on the right side, inset from the edge for Reels/Shorts safety

Default timing:

```text
Standard modes:
  intro_duration: 1.8
  result_duration: 1.0
  end_card_duration: 1.0

one_body_multiple_garments:
  intro_duration: 2.1
  result_duration: 1.5
  end_card_duration: 1.5
```

Each job can override these in `reel`.

## Sample Jobs

Sample jobs live under:

```text
jobs/
  sample_one_garment_multiple_bodies/
  sample_multiple_garments_multiple_bodies/
  sample_video/
  sample_one_body_multiple_garments/
```

Run them with:

```bash
cd /Users/Himanshu/Documents/fashionbot/code
venv/bin/python -m fashionbot.run sample_one_garment_multiple_bodies --dry-run
venv/bin/python -m fashionbot.run sample_multiple_garments_multiple_bodies --dry-run
venv/bin/python -m fashionbot.run sample_video --dry-run
venv/bin/python -m fashionbot.run sample_one_body_multiple_garments --dry-run
```

## Automation Direction

The desired future is a mostly automatic workflow with Google Drive or another
remote storage system.

Possible architecture:

```text
Google Drive job folder
        ->
Mac mini runner / GitHub Actions self-hosted runner / Jenkins / Prefect
        ->
Fashionbot job execution
        ->
Upload outputs back to Google Drive
        ->
Manual YouTube upload
```

The preferred near-term approach is:

```text
GitHub Actions self-hosted runner on Mac mini
```

or:

```text
Jenkins/Prefect on Mac mini
```

The job folder contract is designed to make this easy. A remote orchestrator
only needs to download/create:

```text
jobs/<job_id>/job.json
jobs/<job_id>/inputs/
```

Then run:

```bash
venv/bin/python -m fashionbot.run <job_id>
```

Finally it can upload:

```text
jobs/<job_id>/outputs/
jobs/<job_id>/status.json
```

## Current Cleanup State

The current active repo is intended to be clean and job-based.

Legacy generated media was moved out to:

```text
/Users/Himanshu/Documents/fashionbot_old/cleanup_2026_07_22/
```

The active project should focus on:

```text
assets/
archetypes/
code/fashionbot/
jobs/
README.md
requirements.md
PROJECT_OVERVIEW.md
```

## Good Questions For Future Ideation

Useful prompts to ask another AI assistant:

- How should Fashionbot organize Google Drive job folders?
- Should the orchestrator be GitHub Actions self-hosted runner, Jenkins, Prefect, or something else?
- How should `job.json` evolve for scheduled social content?
- What metadata should be added for YouTube/Instagram captions?
- How should archetypes be tagged by body type, age, style, ethnicity, or vibe?
- How can the `one_body_multiple_garments` mode become a stronger product experience?
- What validation would make this safe for non-technical users?
- What UI would make job creation simple?
- How should output review/approval work before uploading to YouTube?
- How can FAL cost controls and retry behavior be designed?

## Product Direction Notes

The strongest modes right now appear to be:

```text
one_body_multiple_garments
one_garment_multiple_bodies
video
```

`multiple_garments_multiple_bodies` exists, but may be better treated as a
batch/orchestration workflow rather than a primary creative mode.

The most differentiated idea is body-first fashion content:

```text
Start with a body type/persona.
Show many garments on that body.
Help viewers imagine what works for someone like them.
```
