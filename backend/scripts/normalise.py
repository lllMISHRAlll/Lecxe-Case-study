"""Data-cleaning tool for the company database.

    uv run python -m scripts.normalise preview [--change 001]
    uv run python -m scripts.normalise apply --yes [--change 001]
    uv run python -m scripts.normalise rollback --change 001

Preview is the default and changes nothing. Apply needs --yes. Every apply writes a backup,
SQL files and a rollback script to db/changes/<id>_<slug>/ and an entry to DATA_CHANGES.md.
"""

from __future__ import annotations

import argparse
import sys

from app.core.clock import SystemClock
from app.core.config import PROJECT_ROOT, get_settings
from app.db.sessions import Database
from app.normalisation.changes import CHANGES, change_by_id
from app.normalisation.runner import Runner


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=["preview", "apply", "rollback"], nargs="?",
                        default="preview")
    parser.add_argument("--change", help="Change id, e.g. 001. Default: all changes.")
    parser.add_argument("--yes", action="store_true", help="Confirm applying to the company DB.")
    args = parser.parse_args(argv)

    settings = get_settings()
    url = settings.database_url.get_secret_value()
    if not url:
        print("DATABASE_URL is not set in .env", file=sys.stderr)
        return 2
    db = Database.connect(url, sslmode=settings.database_sslmode,
                          statement_timeout_ms=60_000)
    runner = Runner(db, changes_dir=PROJECT_ROOT / "db" / "changes",
                    log_path=PROJECT_ROOT / "DATA_CHANGES.md", clock=SystemClock(),
                    target_label="company DB")
    changes = [change_by_id(args.change)] if args.change else list(CHANGES)

    try:
        if args.action == "rollback":
            if not args.change:
                print("rollback needs --change", file=sys.stderr)
                return 2
            print(f"{changes[0].id}: restored {runner.rollback(changes[0])} row(s)")
            return 0
        for change in changes:
            if args.action == "preview":
                preview = runner.dry_run(change)
                print(f"{change.id} {change.title}: {len(preview.rows)} row(s) would change")
                for row in preview.rows[:5]:
                    print(f"    {row['old']} -> {row['new']}")
                for finding in preview.findings:
                    print(f"    finding: {finding}")
            else:
                result = runner.apply(change, confirmed=args.yes)
                print(f"{change.id} {change.title}: {result.rows_changed} row(s) changed")
                for finding in result.findings:
                    print(f"    finding: {finding}")
    finally:
        db.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
