# Run Requirements

This document lists the files needed to run each Fashionbot mode. The main
command is always:

```bash
cd /Users/Himanshu/Documents/fashionbot/code
python3 run_pipeline.py --id <id>
```

Before running the full pipeline, validate the setup:

```bash
python3 validate_input.py --id <id>
```

## Required For All Modes

Every run needs:

```text
code/input/<id>.json
```

The config must include:

```json
{
  "archetypes": {
    "single_garment_models": "...",
    "garment_batch_models": "...",
    "body_type_model": "...",
    "video_model": "..."
  },
  "vto": {
    "model": "fash or flux",
    "append_garment_name_to_prompt": true,
    "prompt": "required if model is flux"
  }
}
```

`append_garment_name_to_prompt` is optional. When true, each VTO call appends
the garment filename to the prompt, for example `Garment name: wide leg jeans.`

Environment:

```bash
export FAL_KEY="your_key"
```

Alternatively, create `code/.env`:

```bash
FAL_KEY=your_key
```

Optional but commonly used:

```text
Audio/Jazz.mp3
Audio/voiceover_intro.mp3
garments/extras/mascot.png
garments/extras/end.jpg
```

Copyable sample configs:

```text
code/input/example_mode1_single_garment.json
code/input/example_mode2_batch_garments.json
code/input/example_mode3_single_garment_video.json
code/input/example_mode4_body_type_garments.json
```

The sample files use `_sample` objects for human-readable notes because JSON
does not support comments. The pipeline ignores those extra keys.

## Mode 1: Single Garment Image

Detected when this file exists:

```text
garments/og/<id>.jpg
```

And this folder does not exist:

```text
garments/og/<id>/
```

Config requirements:

```json
{
  "archetypes": {
    "single_garment_models": "/path/to/model/folder"
  },
  "vto": {
    "model": "fash or flux",
    "prompt": "required for flux"
  },
  "video": {
    "enabled": false
  }
}
```

Required files/folders:

```text
garments/og/<id>.jpg
archetypes.single_garment_models/
```

`single_garment_models` must contain at least one image:

```text
.png, .jpg, or .jpeg
```

Generated files:

```text
garments/og/<id>.normalized.jpg
garments/<id>/*.jpg
reels/reel_<id>.mp4
```

Reel order:

```text
normalized original garment intro: 1.8 sec
generated VTO images: 1.0 sec each
end card, if present: 1.0 sec
```

Optional intro assets:

```text
Audio/voiceover_intro.mp3
Audio/voiceover_intro.wav
Audio/voiceover_intro.m4a
Audio/voiceover_intro.aac
garments/extras/mascot.png
garments/extras/mascot.jpg
garments/extras/mascot.jpeg
```

If present, the voiceover plays during the intro image and the mascot is
overlaid on that image.

## Mode 2: Batch Garment Folder

Detected when this folder exists:

```text
garments/og/<id>/
```

And this file does not exist:

```text
garments/og/<id>.jpg
```

Config requirements:

```json
{
  "archetypes": {
    "garment_batch_models": "/path/to/model/folder"
  },
  "vto": {
    "model": "fash or flux",
    "prompt": "required for flux"
  },
  "video": {
    "enabled": false
  }
}
```

Required files/folders:

```text
garments/og/<id>/
archetypes.garment_batch_models/
```

The garment folder must contain direct image files:

```text
garments/og/<id>/code_2507:042:679.jpg
garments/og/<id>/code_4437:055:084.jpg
```

The model folder must contain at least one image:

```text
.png, .jpg, or .jpeg
```

Video is not allowed in Mode 2. If `video.enabled=true`, validation fails.

Generated files:

```text
garments/og/<id>/_normalized_garments/*.jpg
garments/<id>/*__*.jpg
reels/reel_<id>.mp4
```

Output naming:

```text
code_2507:042:679.jpg + 34.png
-> garments/<id>/code_2507:042:679__34.jpg
```

Reel order:

```text
normalized garment 1
matching VTO result(s)
normalized garment 2
matching VTO result(s)
end card, if present: 1.0 sec
```

Code labels:

```text
code_2507:042:679 -> 2507/042/679
```

## Mode 3: Single Garment With Video

Detected when:

```text
garments/og/<id>.jpg exists
video.enabled=true
```

And this folder must not exist:

```text
garments/og/<id>/
```

Config requirements:

```json
{
  "archetypes": {
    "single_garment_models": "/path/to/model/folder",
    "video_model": "/path/to/single/video/model.jpg"
  },
  "vto": {
    "model": "fash or flux",
    "prompt": "required for flux"
  },
  "video": {
    "enabled": true,
    "model": "fal-ai/kling-video/v3/standard/image-to-video",
    "prompt": "required video motion prompt",
    "duration": "5",
    "generate_audio": false
  }
}
```

Required files/folders:

```text
garments/og/<id>.jpg
archetypes.single_garment_models/
archetypes.video_model
```

`video_model` must be one image file:

```text
.png, .jpg, or .jpeg
```

Generated files:

```text
garments/og/<id>.normalized.jpg
garments/<id>/*.jpg
garments/<id>/video_source__<video_model_name>.jpg
garments/<id>/videos/video_source__<video_model_name>.mp4
reels/reel_<id>.mp4
```

Reel order:

```text
normalized original garment: 1.8 sec
dedicated VTO image: 1.0 sec
generated video: slowed to 0.75x
end card, if present: 1.0 sec
```

Optional intro voiceover:

```text
Audio/voiceover_intro.mp3
Audio/voiceover_intro.wav
Audio/voiceover_intro.m4a
Audio/voiceover_intro.aac
garments/extras/mascot.png
garments/extras/mascot.jpg
garments/extras/mascot.jpeg
```

If present, the voiceover plays during the intro image, the mascot is overlaid
on that image, and background music starts after the intro image.

## Mode 4: Body Type With Multiple Garments

Detected when config includes:

```json
{
  "mode": "body_type_garments"
}
```

And both of these exist:

```text
garments/og/<id>.jpg
garments/og/<id>/
```

The single image is the original body/reference image shown first in the reel.
The folder contains garments to try on the selected body/avatar model.

Config requirements:

```json
{
  "mode": "body_type_garments",
  "archetypes": {
    "body_type_model": "/path/to/single/body/avatar/model.jpg"
  },
  "vto": {
    "model": "fash or flux",
    "prompt": "required for flux"
  },
  "video": {
    "enabled": false
  }
}
```

Required files/folders:

```text
garments/og/<id>.jpg
garments/og/<id>/
archetypes.body_type_model
```

Generated files:

```text
garments/og/<id>.normalized.jpg
garments/og/<id>/_normalized_garments/*.jpg
garments/<id>/<garment_name>.jpg
reels/reel_<id>.mp4
```

Reel order:

```text
normalized original body/reference image: 2.1 sec
generated VTO images: 1.5 sec each
end card, if present: 1.5 sec
```

Mode 4 intro text:

```text
reel.original_image_description and reel.original_image_credit are centered
in a wide banner around the 3/4 vertical point of the body/reference image.
Generated result clips show the garment filename as a right-side label around
the 3/4 vertical point, inset from the edge for Reels/Shorts UI.
```

Timing params:

```json
"reel": {
  "intro_duration": 2.1,
  "result_duration": 1.5,
  "end_card_duration": 1.5
}
```

Modes 1-3 default to `1.8 / 1.0 / 1.0`. Mode 4 defaults to
`2.1 / 1.5 / 1.5`. Any mode can override those values in `reel`.

## Validation Behavior

`validate_input.py` checks:

```text
config file exists
JSON parses
input mode is unambiguous
required archetype paths exist
model folders contain images
vto.model is valid
vto.prompt exists when using flux
video prompt exists when video is enabled
video duration is valid
Mode 2 does not enable video
planned VTO and video call counts
voiceover availability for modes that use it
Mode 4 body/avatar model exists
```

Validation does not make fal.ai calls.

## Rerun Behavior

The expensive generation scripts skip work when the expected output file already
exists and is non-empty.

For example, if these already exist:

```text
garments/34/4.jpg
garments/34/5.jpg
```

Then rerunning `python3 run_pipeline.py --id 34` does not call fal.ai again for
those VTO images. Delete only the bad output file if you want to regenerate one
specific result.

Mode 3 also skips the generated video if this file already exists:

```text
garments/<id>/videos/video_source__<video_model_name>.mp4
```
