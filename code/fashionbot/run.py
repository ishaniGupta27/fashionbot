import argparse
from contextlib import contextmanager
from datetime import datetime
import os
from pathlib import Path
import sys
import traceback

from .errors import FashionbotError
from .job import load_job
from .remote import (
    pull_remote_inputs,
    push_remote_job,
    rclone_bin_from_env,
    remote_root_from_env,
)
from .runner import run_job
from .settings import ASSETS_DIR, archetypes_dir, jobs_dir


class TeeStream:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
        return len(data)

    def flush(self):
        for stream in self.streams:
            stream.flush()

    def isatty(self):
        return any(getattr(stream, "isatty", lambda: False)() for stream in self.streams)

    @property
    def encoding(self):
        return getattr(self.streams[0], "encoding", None)

    def fileno(self):
        return self.streams[0].fileno()


def run_log_path(jobs_root, job_id):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"run_{timestamp}_{os.getpid()}.log"
    return Path(jobs_root) / str(job_id) / "logs" / filename


@contextmanager
def tee_to_log(log_path):
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("a", buffering=1) as log_file:
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = TeeStream(original_stdout, log_file)
        sys.stderr = TeeStream(original_stderr, log_file)

        try:
            yield
        finally:
            sys.stdout.flush()
            sys.stderr.flush()
            sys.stdout = original_stdout
            sys.stderr = original_stderr


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
    parser.add_argument(
        "--remote",
        action="store_true",
        help="Pull assets/archetypes/job from remote storage and push the job back.",
    )
    parser.add_argument(
        "--remote-root",
        default=None,
        help="Remote root such as gdrive:Fashionbot. Defaults to FASHIONBOT_REMOTE_ROOT.",
    )
    parser.add_argument(
        "--rclone-bin",
        default=None,
        help="rclone executable path. Defaults to FASHIONBOT_RCLONE_BIN or rclone.",
    )

    args = parser.parse_args(argv)
    job_id = args.job_id or args.job_id_flag
    if not job_id:
        parser.error("job id is required")

    active_jobs_dir = args.jobs_dir or jobs_dir()
    active_archetypes_dir = args.archetypes_dir or archetypes_dir()
    active_remote_root = args.remote_root or remote_root_from_env()
    active_rclone_bin = args.rclone_bin or rclone_bin_from_env()
    log_path = run_log_path(active_jobs_dir, job_id)
    remote_job_ready = False

    with tee_to_log(log_path):
        print(f"Run log: {log_path}")

        try:
            if args.remote:
                if not active_remote_root:
                    raise FashionbotError(
                        "--remote requires --remote-root or FASHIONBOT_REMOTE_ROOT"
                    )

                print("\nREMOTE MODE ENABLED")
                print(f"Remote root: {active_remote_root}")
                print(f"rclone: {active_rclone_bin}")
                print(f"Local assets: {ASSETS_DIR}")
                print(f"Local archetypes: {active_archetypes_dir}")
                print(f"Local jobs: {active_jobs_dir}")

                pull_remote_inputs(
                    job_id,
                    active_remote_root,
                    active_jobs_dir,
                    active_archetypes_dir,
                    ASSETS_DIR,
                    active_rclone_bin,
                )
                remote_job_ready = True

            job = load_job(job_id, active_jobs_dir, active_archetypes_dir)
            outputs = run_job(job, dry_run=args.dry_run)
        except FashionbotError as e:
            print(f"\nERROR: {e}", file=sys.stderr)
            return_code = 1
        except Exception as e:
            print(f"\nUNEXPECTED ERROR: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return_code = 1
        else:
            print("\nDONE")
            if outputs.get("reel"):
                print(f"Final reel: {outputs['reel']}")
            return_code = 0

        if args.remote and remote_job_ready:
            try:
                push_remote_job(
                    job_id,
                    active_remote_root,
                    active_jobs_dir,
                    active_rclone_bin,
                )
            except FashionbotError as e:
                print(f"\nERROR: {e}", file=sys.stderr)
                return_code = 1

    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
