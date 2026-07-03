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
    "prompt": "required if model is flux"
  }
}
```

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
generated VTO images
end card, if present
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
end card, if present
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
dedicated VTO image: 1 sec
generated video: slowed to 0.75x
end card, if present
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
garments/og/<id>/_normalized_garments/*.jpg
garments/<id>/<garment_name>.jpg
reels/reel_<id>.mp4
```

Reel order:

```text
original body/reference image: 1.8 sec
generated VTO images
end card, if present
```

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
