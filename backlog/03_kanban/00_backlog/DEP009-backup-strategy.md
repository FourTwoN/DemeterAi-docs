# [DEP009] Backup Strategy (PostgreSQL + S3)

## Metadata

- **Epic**: epic-011-deployment
- **Sprint**: Sprint-07
- **Priority**: `critical` ⚡
- **Complexity**: M (5 points)
- **Dependencies**: Blocked by [F006]

## Description

Implement automated backup strategy: PostgreSQL daily backups, S3 lifecycle policies, point-in-time
recovery.

## Acceptance Criteria

- [ ] **PostgreSQL backups**:
    - Daily full backups (pg_dump)
    - Retention: 30 days local, 1 year S3
    - WAL archiving for PITR (point-in-time recovery)
    - RPO: 5 minutes, RTO: 30-60 minutes

- [ ] **S3 lifecycle policies**:
    - Original photos: Delete after 90 days
    - Processed photos: Delete after 365 days
    - Transition to Glacier after 30 days

- [ ] **Backup verification**:
    - Weekly restore test (dev environment)
    - Backup integrity checks
    - Monitoring alerts on backup failure

## Implementation

**PostgreSQL backup script:**

```bash
#!/bin/bash
# /scripts/backup_db.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="demeterai_${DATE}.sql.gz"

# Full backup
pg_dump -h $DB_HOST -U $DB_USER demeterai | gzip > /backups/${BACKUP_FILE}

# Upload to S3
aws s3 cp /backups/${BACKUP_FILE} s3://demeterai-backups/database/

# Delete local backups older than 30 days
find /backups -name "*.sql.gz" -mtime +30 -delete
```

**Cron schedule:**

```
0 2 * * * /scripts/backup_db.sh >> /var/log/backup.log 2>&1
```

**WAL archiving (postgresql.conf):**

```
wal_level = replica
archive_mode = on
archive_command = 'aws s3 cp %p s3://demeterai-backups/wal/%f'
```

**S3 lifecycle policy:**

```json
{
  "Rules": [
    {
      "Id": "DeleteOriginalPhotos",
      "Filter": {"Prefix": "original/"},
      "Status": "Enabled",
      "Expiration": {"Days": 90}
    },
    {
      "Id": "ArchiveProcessedPhotos",
      "Filter": {"Prefix": "processed/"},
      "Status": "Enabled",
      "Transitions": [
        {"Days": 30, "StorageClass": "GLACIER"}
      ],
      "Expiration": {"Days": 365}
    }
  ]
}
```

## Testing

- Run backup script manually
- Verify backup uploaded to S3
- Test restore: `pg_restore backup.sql.gz`
- Test PITR: Restore to specific timestamp
- Test S3 lifecycle policy applies

---
**Card Created**: 2025-10-09
