#!/bin/sh
# 在服务器仓库根目录执行。打一份 Postgres 自定义格式副本到导出落点。
# 定时默认不要装。要装时用 backup-postgres.cron.example，并先设 BACKUP_SCHEDULE_ENABLED。
set -e
ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
. ./.env 2>/dev/null || true
DEST="${BACKUP_HOST_DIR:-/opt/g-snipers-db-exports}"
mkdir -p "$DEST"
STAMP="$(date -u +%Y%m%d-%H%M%S)"
FILE="$DEST/gsnipers-db-$STAMP.dump"
docker compose exec -T postgres pg_dump -U gsnipers -d gsnipers -Fc > "$FILE"
echo "wrote $FILE"

KIND="${BACKUP_OFFSITE_KIND:-none}"
if [ "$KIND" = "dir" ] && [ -n "${BACKUP_OFFSITE_DIR:-}" ]; then
  mkdir -p "$BACKUP_OFFSITE_DIR"
  cp "$FILE" "$BACKUP_OFFSITE_DIR/"
  echo "copied to $BACKUP_OFFSITE_DIR"
fi
if [ "$KIND" = "scp" ] && [ -n "${BACKUP_OFFSITE_SCP:-}" ]; then
  scp -o BatchMode=yes "$FILE" "$BACKUP_OFFSITE_SCP/"
  echo "copied to $BACKUP_OFFSITE_SCP"
fi
