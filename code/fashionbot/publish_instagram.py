import argparse

from .errors import FashionbotError
from .instagram import publish_reel
from .job import load_job
from .remote import rclone_bin_from_env, remote_root_from_env
from .runlog import run_log_path, tee_to_log
from .settings import archetype_metadata_dir, archetypes_dir, jobs_dir


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Publish a Fashionbot reel as an Instagram Reel."
    )
    parser.add_argument("job_id", help="Job folder name under jobs/")
    parser.add_argument("--jobs-dir", default=None, help="Override FASHIONBOT_JOBS_DIR")
    parser.add_argument(
        "--archetypes-dir",
        default=None,
        help="Override FASHIONBOT_ARCHETYPES_DIR",
    )
    parser.add_argument(
        "--archetype-metadata-dir",
        default=None,
        help="Override FASHIONBOT_ARCHETYPE_METADATA_DIR",
    )
    parser.add_argument(
        "--remote-root",
        default=None,
        help="rclone remote root used to build the public video URL "
        "(defaults to FASHIONBOT_REMOTE_ROOT).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Publish even if outputs/instagram_upload.json already exists.",
    )

    args = parser.parse_args(argv)

    active_jobs_dir = args.jobs_dir or jobs_dir()
    remote_root = args.remote_root or remote_root_from_env()
    log_path = run_log_path(active_jobs_dir, args.job_id, prefix="publish_instagram")

    with tee_to_log(log_path):
        print(f"Publish log: {log_path}")
        try:
            job = load_job(
                args.job_id,
                active_jobs_dir,
                args.archetypes_dir or archetypes_dir(),
                args.archetype_metadata_dir or archetype_metadata_dir(),
            )
            publish_reel(
                job,
                remote_root=remote_root,
                rclone_bin=rclone_bin_from_env(),
                force=args.force,
            )
        except FashionbotError as e:
            print(f"ERROR: {e}")
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
