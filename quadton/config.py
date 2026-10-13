from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    discord_token: str
    database_path: str
    log_level: str
    admin_user_ids: tuple[int, ...]
    backup_dir: str
    environment: str

    @classmethod
    def from_env(cls) -> "Config":
        token = os.environ.get("DISCORD_TOKEN", "").strip()
        if not token:
            raise RuntimeError("DISCORD_TOKEN is required")
        admins_raw = os.environ.get("QUADTON_ADMIN_IDS", "").strip()
        admin_ids = tuple(
            int(x) for x in admins_raw.split(",") if x.strip().lstrip("-").isdigit()
        )
        return cls(
            discord_token=token,
            database_path=os.environ.get("QUADTON_DB_PATH", "quadton.db").strip(),
            log_level=os.environ.get("QUADTON_LOG_LEVEL", "INFO").upper(),
            admin_user_ids=admin_ids,
            backup_dir=os.environ.get("QUADTON_BACKUP_DIR", "backups").strip(),
            environment=os.environ.get("QUADTON_ENV", "production").strip(),
        )
