# Fashionbot

Fashionbot is a local pipeline for turning garment images into short fashion
reels. It normalizes garment photos, generates virtual try-on images with
fal.ai, can optionally generate one video from a VTO still, and builds a final
vertical reel with audio.

The main command is intentionally simple:

```bash
cd /Users/Himanshu/Documents/fashionbot/code
python3 run_pipeline.py --id 33
```

All creative and model choices for a run live in:

```text
code/input/{id}.json
```

## What It Does

The pipeline can run four internal modes.

### Mode 1: Single Garment Image

Input:

```text
garments/og/{id}.jpg
```

Flow:

```text
normalize garment
generate VTO images against archetypes.single_garment_models
build reel from generated images
```

Output:

```text
garments/{id}/*.jpg
reels/reel_{id}.mp4
```

### Mode 2: Batch Garment Folder

Input:

```text
garments/og/{id}/
```

Flow:

```text
normalize each garment into garments/og/{id}/_normalized_garments
generate garment x model VTO images
build grouped reel
```

Output naming:

```text
code_2507:042:679.jpg + 34.png
-> garments/{id}/code_2507:042:679__34.jpg
```

Labels in reels:

```text
code_2507:042:679 -> 2507/042/679
```

Video is intentionally not allowed in this mode.

### Mode 3: Single Garment With Video

Input:

```text
garments/og/{id}.jpg
```

Config:

```json
"video": {
  "enabled": true
}
```

Flow:

```text
normalize garment
generate one dedicated VTO still using archetypes.video_model
generate one Kling image-to-video asset
build reel: original image, VTO still, video, end card
```

Outputs:

```text
garments/{id}/video_source__{video_model_name}.jpg
garments/{id}/videos/video_source__{video_model_name}.mp4
reels/reel_{id}.mp4
```

### Mode 4: Body Type With Multiple Garments

Input:

```text
garments/og/{id}.jpg      original body/reference image for reel intro
garments/og/{id}/         garment folder
```

Config:

```json
"mode": "body_type_garments",
"archetypes": {
  "body_type_model": "/path/to/avatar-or-model-image.jpg"
}
```

Flow:

```text
normalize original body/reference image
normalize each garment
generate each garment on one body/avatar model image
build reel: normalized body/reference image, generated VTO images, end card
```

Mode 4 uses a special intro text treatment: `reel.original_image_description`
and `reel.original_image_credit` are horizontally centered in a wide banner
placed around the 3/4 vertical point of the original body/reference image.
Generated Mode 4 result clips also show the garment filename as a right-side
label around the 3/4 vertical point, inset from the edge for Reels/Shorts UI.

Output:

```text
garments/og/{id}.normalized.jpg
garments/og/{id}/_normalized_garments/*.jpg
garments/{id}/*.jpg
reels/reel_{id}.mp4
```

## Config File

Create one JSON file per run:

```text
code/input/33.json
```

Each real run file is named by id, for example `code/input/63.json`.
The repo also includes copyable sample configs:

```text
code/input/example_mode1_single_garment.json
code/input/example_mode2_batch_garments.json
code/input/example_mode3_single_garment_video.json
code/input/example_mode4_body_type_garments.json
```

Those sample files include `_sample` notes. JSON does not support comments, so
the `_sample` object is used as readable documentation and is ignored by the
pipeline.

Minimal shared shape:

```json
{
  "archetypes": {
    "single_garment_models": "/Users/Himanshu/Documents/fashionbot/archetypes/final",
    "garment_batch_models": "/Users/Himanshu/Documents/fashionbot/archetypes/model",
    "body_type_model": "/Users/Himanshu/Documents/fashionbot/archetypes/body_types/model.jpg",
    "video_model": "/Users/Himanshu/Documents/fashionbot/archetypes/video/model.jpg"
  },
  "vto": {
    "model": "flux",
    "append_garment_name_to_prompt": false,
    "prompt": "Describe the garment and styling requirements for virtual try-on."
  },
  "video": {
    "enabled": false,
    "model": "fal-ai/kling-video/v3/standard/image-to-video",
    "prompt": "Describe the motion for the generated fashion video.",
    "duration": "5",
    "generate_audio": false
  },
  "reel": {
    "use_audio": true,
    "include_end_card": true,
    "intro_duration": 1.8,
    "result_duration": 1.0,
    "end_card_duration": 1.0,
    "original_image_description": "Original garment photo description",
    "original_image_credit": "Photographer or source name"
  }
}
```

`video` can be omitted entirely. Missing video config means video is disabled.
`vto.append_garment_name_to_prompt` is optional. When true, the generator adds
the garment filename to each VTO prompt, for example
`Garment name: wide leg jeans.` This is useful for batch and Mode 4 runs where
filenames carry garment semantics.
`reel.intro_duration`, `reel.result_duration`, and
`reel.end_card_duration` are optional timing controls in seconds. Modes 1-3
default to `1.8 / 1.0 / 1.0`; Mode 4 defaults to `2.1 / 1.5 / 1.5`.
`reel.original_image_description` and `reel.original_image_credit` are optional.
When present, they are rendered on the original garment image clip only, with
the description above the credit. Mode 4 uses the centered 3/4-height banner
described above.

## Folder Layout

Important folders:

```text
Audio/
  Jazz.mp3
  voiceover_intro.mp3        optional

archetypes/
  final/                     common Mode 1 model set
  model/                     common Mode 2 model set
  body_types/                suggested home for Mode 4 body/avatar images
  video/                     suggested home for video_model

code/
  input/
    example.json
    example_mode1_single_garment.json
    example_mode2_batch_garments.json
    example_mode3_single_garment_video.json
    example_mode4_body_type_garments.json
    {id}.json

garments/
  og/
    {id}.jpg                 Mode 1 or Mode 3 input
    {id}.jpg + {id}/          Mode 4 body image + garment folder
    {id}/                    Mode 2 or Mode 4 input folder
      code_2507:042:679.jpg
      _normalized_garments/
  {id}/                      generated VTO outputs
    videos/                  generated video outputs
  extras/
    end.jpg

reels/
  reel_{id}.mp4
```

## Scripts

`run_pipeline.py`

Main entrypoint. Loads config, validates input, detects the internal mode,
runs normalization, VTO generation, optional video generation, and reel build.

`validate_input.py`

Chatty preflight check. It runs before expensive fal.ai calls and reports
detected mode, paths, prompts, guardrails, and planned call counts.

`pipeline_config.py`

Shared paths, file helpers, and internal mode map. This is where the four
pipeline modes and their feature flags live.

`normalize.py`

Places a garment image on a 1080x1920 gray canvas. Supports optional
`--output` for batch normalization.

`generate_vto.py`

Calls fal.ai VTO APIs. Supports:

```text
one garment -> many models
many garments -> many models
one garment -> one model
many garments -> one model
```

`generate_video.py`

Calls fal.ai Kling image-to-video for one selected VTO still. Always asks for
confirmation before making the video call.

`build_reel_audio.py`

Builds the final vertical reel with audio. Supports image reels, grouped batch
reels, and featured video reels. In featured video mode, it uses:

```text
original image: 1.8s by default
VTO still: 1.0s by default
generated video: slowed to 0.75x
end card: 1.0s by default
```

If `Audio/voiceover_intro.*` exists, it plays during the first image and the
background music starts after the intro.

## Environment

Use the project venv from `code/`:

```bash
cd /Users/Himanshu/Documents/fashionbot/code
source venv/bin/activate
```

Set your fal.ai key:

```bash
export FAL_KEY="your_key"
```

Or save it locally in `code/.env`:

```bash
FAL_KEY=your_key
```

## Typical Workflow

1. Add input image or folder:

```text
garments/og/33.jpg
```

or:

```text
garments/og/33/
```

2. Create config:

```text
code/input/33.json
```

3. Validate:

```bash
python3 validate_input.py --id 33
```

4. Run:

```bash
python3 run_pipeline.py --id 33
```

## Contributing Notes

- Keep user-facing commands simple. Prefer putting creative settings in
  `code/input/{id}.json`.
- Add new mode behavior to `PIPELINE_MODES` in `pipeline_config.py` first.
- Keep guardrails in `validate_input.py` before adding expensive API calls.
- Preserve Mode 2 as the simple batch/catalog flow. Avoid adding intro,
  voiceover, mascot, or video features there unless intentionally changing the
  product behavior.
- Use direct file scanning for garment batch folders. Filenames such as
  `code_2507:042:679.jpg` are expected and are displayed as `2507/042/679`.
- For any new fal.ai model, confirm the API schema before wiring arguments.
