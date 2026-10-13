from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path

from quadton.db.database import Database

log = logging.getLogger(__name__)


class BackupService:
    def __init__(self, db: Database, backup_dir: str, retain: int = 14) -> None:
        self.db = db
        self.dir = Path(backup_dir)
        self.retain = retain

    def backup(self) -> Path:
        """Uses SQLite's native backup via the sync connection.

        Runs synchronously; call from a thread if needed.
        """
        self.dir.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
        target = self.dir / f"quadton-{stamp}.db"
        # VACUUM INTO gives a consistent snapshot.
        conn = self.db.conn
        conn._conn.execute(f"VACUUM INTO '{target}'")  # type: ignore[attr-defined]
        self._prune()
        return target

    def _prune(self) -> None:
        files = sorted(self.dir.glob("quadton-*.db"))
        for old in files[: max(0, len(files) - self.retain)]:
            try:
                old.unlink()
            except OSError as e:
                log.warning("failed to prune backup %s: %s", old, e)

    def verify(self, path: Path) -> bool:
        """Quick check that a backup file exists and is a readable SQLite file."""
        import sqlite3
        if not path.exists():
            return False
        try:
            c = sqlite3.connect(str(path))
            cur = c.execute("PRAGMA integrity_check")
            ok = cur.fetchone()[0] == "ok"
            c.close()
            return ok
        except sqlite3.Error:
            return False
