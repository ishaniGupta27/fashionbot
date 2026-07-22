# Job Templates

These folders show the exact structure expected under `jobs/<job_id>/`.

To start a new job, copy one template folder into `jobs/` or into the matching
remote folder under `Fashionbot/jobs/`, then rename it to the job id.

Example:

```text
job_templates/one_body_multiple_garments/
  job.json
  inputs/
    original.jpg
    garments/
      baggy-jeans.jpg
      straight-jeans.jpg
      wide-leg-jeans.jpg
```

Runtime jobs live in `jobs/` locally or in remote storage. The `jobs/` folder is
not tracked in Git.

In `one_body_multiple_garments`, `inputs.original_image` is optional. If it is
not present in `job.json`, Fashionbot uses `models.archetype_id` as the intro
image.
