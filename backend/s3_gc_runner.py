import argparse
import json

from tasks import garbage_collect_s3_orphans


def main():
    parser = argparse.ArgumentParser(
        description="S3 garbage collector for orphaned PDF artifacts."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete objects (default is dry-run).",
    )
    parser.add_argument(
        "--min-age-hours",
        type=int,
        default=24,
        help="Only delete orphan objects older than this age.",
    )
    args = parser.parse_args()

    result = garbage_collect_s3_orphans(
        dry_run=not args.apply,
        min_age_hours=args.min_age_hours,
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
