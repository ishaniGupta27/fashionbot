import argparse
import sys

from .errors import FashionbotError
from .job import load_job
from .runner import run_job
from .settings import archetypes_dir, jobs_dir


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run a Fashionbot job by job id."
    )
    parser.add_argument("job_id", nargs="?", help="Job folder name under jobs/")
    parser.add_argument("--job-id", dest="job_id_flag", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--jobs-dir", default=None, help="Override FASHIONBOT_JOBS_DIR")
    parser.add_argument(
        "--archetypes-dir",
        default=None,
        help="Override FASHIONBOT_ARCHETYPES_DIR",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip fal.ai calls and create local mock outputs.",
    )

    args = parser.parse_args(argv)
    job_id = args.job_id or args.job_id_flag
    if not job_id:
        parser.error("job id is required")

    active_jobs_dir = args.jobs_dir or jobs_dir()
    active_archetypes_dir = args.archetypes_dir or archetypes_dir()

    try:
        job = load_job(job_id, active_jobs_dir, active_archetypes_dir)
        outputs = run_job(job, dry_run=args.dry_run)
    except FashionbotError as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        return 1

    print("\nDONE")
    if outputs.get("reel"):
        print(f"Final reel: {outputs['reel']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
