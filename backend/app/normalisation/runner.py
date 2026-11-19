"""Runs data-cleaning changes safely: preview, backup, apply + verify in one transaction,
rollback script, and an entry in the change log."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import Connection, text

from app.core.clock import Clock
from app.db.sessions import Database
from app.normalisation.changes import CHANGES, Change, lit

NULL = r"\N"


class NotConfirmedError(RuntimeError):
    """Applying a change needs an explicit confirmation."""


class VerificationFailedError(RuntimeError):
    """Verification found rows still needing the change; the transaction was rolled back."""


@dataclass
class Preview:
    rows: list[dict] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)


@dataclass
class ApplyResult:
    rows_changed: int
    findings: list[str]


class Runner:
    def __init__(self, db: Database, *, changes_dir: Path | None, log_path: Path | None,
                 clock: Clock, target_label: str) -> None:
        self._db = db
        self._changes_dir = changes_dir
        self._log_path = log_path
        self._clock = clock
        self._target = target_label

    # ------------------------------------------------------------------ public API

    def dry_run(self, change: Change) -> Preview:
        with self._db.read_engine.connect() as conn:
            return self._preview(conn, change)

    def apply(self, change: Change, *, confirmed: bool = False) -> ApplyResult:
        if not confirmed:
            raise NotConfirmedError(f"Change {change.id} needs confirmed=True to apply")
        with self._db.write_engine.begin() as conn:
            preview = self._preview(conn, change)
            backup_csv = self._backup_csv(change, preview.rows)
            changed = conn.execute(text(change.apply_sql)).rowcount
            remaining = conn.execute(text(change.verify_sql)).scalar()
            if remaining:
                raise VerificationFailedError(
                    f"Change {change.id}: {remaining} row(s) still need changing")
        self._record(change, preview, backup_csv, changed)
        return ApplyResult(rows_changed=changed, findings=preview.findings)

    def apply_all(self, *, confirmed: bool = False) -> list[ApplyResult]:
        return [self.apply(change, confirmed=confirmed) for change in CHANGES]

    def rollback(self, change: Change) -> int:
        rows = self._read_backup(change)
        sets = ", ".join(f"{c.column} = CAST(:{c.column} AS {c.cast})" for c in change.columns)
        statement = text(f"UPDATE {change.table} SET {sets} WHERE id = :id")
        with self._db.write_engine.begin() as conn:
            for row in reversed(rows):
                conn.execute(statement, row)
        self._log(f"## {change.id} {change.title}: rolled back\n\n"
                  f"- When: {self._stamp()}\n- Target: {self._target}\n"
                  f"- Rows restored: {len(rows)}\n")
        return len(rows)

    # ------------------------------------------------------------------ internals

    def _preview(self, conn: Connection, change: Change) -> Preview:
        result = conn.execute(text(change.preview_sql)).mappings().all()
        rows = [
            {"id": r["id"],
             "old": {c.column: r[f"old_{c.column}"] for c in change.columns},
             "new": {c.column: r[f"new_{c.column}"] for c in change.columns}}
            for r in result
        ]
        findings = []
        if change.findings_sql:
            findings = [r[0] for r in conn.execute(text(change.findings_sql)).all()]
        return Preview(rows=rows, findings=findings)

    def _backup_csv(self, change: Change, rows: list[dict]) -> str:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        for row in rows:
            writer.writerow([row["id"], *(_csv_value(row["old"][c.column])
                                          for c in change.columns)])
        return buffer.getvalue()

    def _folder(self, change: Change) -> Path | None:
        if self._changes_dir is None:
            return None
        folder = self._changes_dir / change.folder
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def _record(self, change: Change, preview: Preview, backup_csv: str, changed: int) -> None:
        folder = self._folder(change)
        if folder is None:
            return
        backup = folder / "backup.csv"
        if changed:
            header = "" if backup.exists() else ",".join(
                ["id", *(c.column for c in change.columns)]) + "\n"
            with backup.open("a", newline="") as fh:
                fh.write(header + backup_csv)
        (folder / "apply.sql").write_text(change.apply_sql + ";\n")
        (folder / "verify.sql").write_text(change.verify_sql + ";\n")
        (folder / "rollback.sql").write_text(self._rollback_sql(change))
        findings = "".join(f"  - {f}\n" for f in preview.findings) or "  - none\n"
        self._log(
            f"## {change.id} {change.title}\n\n"
            f"- When: {self._stamp()}\n- Target: {self._target}\n"
            f"- Table: {change.table} ({', '.join(c.column for c in change.columns)})\n"
            f"- Reason: {change.reason}\n- Rows changed: {changed}\n"
            f"- Backup: db/changes/{change.folder}/backup.csv\n"
            f"- Roll back: `make normalise-rollback CHANGE={change.id}` "
            f"(or run db/changes/{change.folder}/rollback.sql)\n"
            f"- Findings left for a business decision:\n{findings}"
        )

    def _read_backup(self, change: Change) -> list[dict]:
        folder = self._folder(change)
        if folder is None or not (folder / "backup.csv").exists():
            return []
        with (folder / "backup.csv").open(newline="") as fh:
            return [{k: (None if v == NULL else v) for k, v in row.items()}
                    for row in csv.DictReader(fh)]

    def _rollback_sql(self, change: Change) -> str:
        statements = []
        for row in reversed(self._read_backup(change)):
            sets = ", ".join(
                f"{c.column} = " + ("NULL" if row[c.column] is None
                                    else f"CAST({lit(row[c.column])} AS {c.cast})")
                for c in change.columns
            )
            statements.append(f"UPDATE {change.table} SET {sets} WHERE id = {lit(row['id'])};")
        body = "\n".join(statements) or "-- nothing to roll back"
        return f"-- Restores the values saved in backup.csv for change {change.id}\nBEGIN;\n" \
               f"{body}\nCOMMIT;\n"

    def _log(self, entry: str) -> None:
        if self._log_path is None:
            return
        if not self._log_path.exists():
            self._log_path.write_text(
                "# Data changes\n\nEvery change made to company data, newest last.\n\n")
        with self._log_path.open("a") as fh:
            fh.write(entry + "\n")

    def _stamp(self) -> str:
        return self._clock.now().strftime("%Y-%m-%d %H:%M UTC")


def _csv_value(value: str | None) -> str:
    return NULL if value is None else value
