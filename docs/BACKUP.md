# Backup and Recovery

## Creating a backup
- Admin command: `/admin-backup` (writes a `VACUUM INTO` snapshot, then runs
  `PRAGMA integrity_check` on the new file).
- Manual: stop the bot, copy `quadton.db`, `quadton.db-wal`, `quadton.db-shm`
  together. Better: `sqlite3 quadton.db "VACUUM INTO 'quadton-backup.db'"`.

## Retention
`BackupService` keeps the most recent 14 files matching `quadton-*.db` and
deletes older ones.

## Storing off-device
Copy `QUADTON_BACKUP_DIR` to a location outside the host (rclone, scp,
external storage). The bot does **not** ship off-device transfer — wire it up
to your preferred tool.

## Restoring
1. Stop the bot.
2. Move the current DB aside: `mv quadton.db quadton.db.broken`.
3. Copy the backup in: `cp backups/quadton-YYYYMMDD-HHMMSS.db quadton.db`.
4. Delete stale `-wal`/`-shm` files if present.
5. Start the bot and run `/admin-integrity`.

## Verifying
Always verify a backup by opening it read-only and running
`PRAGMA integrity_check;` — expected output is `ok`. The `BackupService.verify`
helper does exactly that.
