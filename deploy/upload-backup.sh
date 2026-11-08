#!/bin/sh
# Copies the newest nightly database backup to S3, so losing the VM doesn't lose the data.
# Runs from the riceflow user's crontab at 2:30 AM, after the 2 AM dump.
# --with-data also copies data/harvests.csv, which isn't in git. Run that by hand when it changes.
# Keys live in .aws-backup.env (mode 600). They can only upload to this one bucket.
set -eu
cd /opt/riceflow

BUCKET=riceflow-db-backups-2026
REGION=ap-southeast-2
AWS_CLI=amazon/aws-cli:2.22.35

fail() {
  echo "$(date -u +%FT%TZ) FAILED: $1"
  exit 1
}

upload() {  # upload <local path> <S3 key>
  etag=$(docker run --rm --env-file .aws-backup.env -e AWS_DEFAULT_REGION="$REGION" \
    -v "$PWD/backups:/in/backups:ro" -v "$PWD/data:/in/data:ro" "$AWS_CLI" \
    s3api put-object --bucket "$BUCKET" --key "$2" --body "/in/$1" --query ETag --output text | tr -d '"')
  # S3's ETag is the file's MD5 here, so a match proves S3 stored the same bytes
  [ "$etag" = "$(md5sum "$1" | cut -d' ' -f1)" ] || fail "$1 did not reach S3 intact"
  echo "$(date -u +%FT%TZ) uploaded $1"
}

latest=$(ls -1t backups/riceflow-*.sql.gz | head -1)
# Older than 26 hours means last night's dump didn't run
[ -n "$(find "$latest" -mmin -1560)" ] || fail "newest backup $latest is too old"
upload "$latest" "database/$(basename "$latest")"

if [ "${1:-}" = "--with-data" ]; then
  upload data/harvests.csv data/harvests.csv
fi
