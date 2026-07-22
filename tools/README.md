# Tools

## submit_job.py

Uploads a local numeric job folder to Google Drive using the Drive API, then
triggers the GitHub Actions workflow using the GitHub API.

No `rclone` or `gh` CLI is required on the submit machine.

Example:

```bash
python tools/submit_job.py \
  --job-folder /path/to/2 \
  --creds ~/fashionbot_submit_creds.json
```

Real fal.ai run:

```bash
python tools/submit_job.py \
  --job-folder /path/to/2 \
  --creds ~/fashionbot_submit_creds.json \
  --real
```

Rules:

```text
folder name must be numeric
/path/to/2 -> job_id 2
job folder must contain job.json
job folder must contain inputs/
```

The tool uploads to:

```text
<google_drive.root_path>/jobs/<job_id>
```

It then triggers:

```text
.github/workflows/run-fashionbot.yml
```

The tool writes an exhaustive local submit log under:

```text
<job-folder>/logs/local_submit_YYYYMMDD_HHMMSS.log
```

Create your private creds file from:

```text
tools/submit_job.example.json
```

Never commit the real creds file. It contains long-lived Google and GitHub
tokens.
