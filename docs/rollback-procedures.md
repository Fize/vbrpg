# Deployment Rollback Procedures

## Overview

This document describes how to rollback a failed VBRPG deployment, including database migration reversals and service recovery.

---

## When to Rollback

Perform a rollback if:
- ✅ Database migration fails during deployment
- ✅ Post-deployment health checks fail
- ✅ Critical bugs discovered in production
- ✅ Performance degradation after deployment
- ✅ Data integrity issues detected

**DO NOT rollback if:**
- ❌ Minor UI bugs that don't affect core functionality
- ❌ Non-critical performance issues
- ❌ Issues resolved by configuration changes only

---

## Rollback Types

### 1. Database Migration Rollback (Most Common)

**Scenario**: Migration failed or caused data issues

**Steps**:

```bash
# Navigate to backend directory
cd backend

# Check current migration version
alembic current

# Rollback one migration
alembic downgrade -1

# Verify rollback
alembic current

# Restart backend service
sudo systemctl restart vbrpg-backend  # Production
# OR
docker-compose restart backend        # Docker
# OR
uvicorn src.main:app --reload        # Development
```

**Rollback to Specific Version**:
```bash
# Find migration hash from alembic/versions/ directory
ls alembic/versions/

# Rollback to specific version
alembic downgrade <migration_hash>

# Example: Rollback to version before Feature 002
alembic downgrade 1a2b3c4d5e6f
```

**Rollback All Migrations** (Nuclear Option):
```bash
# WARNING: This removes all database schema
alembic downgrade base

# Restore from backup (see section below)
```

---

### 2. Full Service Rollback

**Scenario**: Entire deployment needs to be reverted

**Production (systemd)**:

```bash
# Step 1: Stop current service
sudo systemctl stop vbrpg-backend

# Step 2: Restore previous application version
cd /opt/vbrpg
git checkout <previous_commit_hash>  # OR git checkout main~1

# Step 3: Restore database from backup
cd backend
cp data/backups/vbrpg_backup_<timestamp>.db data/vbrpg.db

# Step 4: Verify database version matches code
alembic current  # Should match code version

# Step 5: Restart service
sudo systemctl start vbrpg-backend

# Step 6: Verify health
curl http://localhost:8000/health
```

**Docker Deployment**:

```bash
# Step 1: Stop containers
docker-compose down

# Step 2: Restore previous image version
docker-compose pull backend:previous-tag

# Step 3: Restore database volume
docker cp vbrpg_backup_<timestamp>.db vbrpg_backend:/app/data/vbrpg.db

# Step 4: Start containers
docker-compose up -d

# Step 5: Verify health
curl http://localhost:8000/health
```

---

### 3. Database Restore from Backup

**Scenario**: Database corrupted or migration irreversible

**Automatic Backup Location**: `backend/data/backups/vbrpg_backup_<timestamp>.db`

**Restore Steps**:

```bash
# Step 1: Stop backend service
sudo systemctl stop vbrpg-backend  # OR docker-compose stop backend

# Step 2: Backup current (corrupted) database
cd backend/data
mv vbrpg.db vbrpg_corrupted_$(date +%Y%m%d_%H%M%S).db

# Step 3: Restore from backup
cp backups/vbrpg_backup_<timestamp>.db vbrpg.db

# Step 4: Verify database integrity
sqlite3 vbrpg.db "PRAGMA integrity_check;"

# Step 5: Check migration version
cd ..
alembic current

# Step 6: Restart service
sudo systemctl start vbrpg-backend

# Step 7: Verify health
curl http://localhost:8000/health
```

**Manual Backup (if automatic failed)**:

```bash
# Find latest backup
ls -lt backend/data/backups/

# Identify backup before failed deployment
# Filename format: vbrpg_backup_YYYYMMDD_HHMMSS.db
# Example: vbrpg_backup_20251109_143022.db

# Restore using timestamp from before deployment
cp backups/vbrpg_backup_20251109_143022.db vbrpg.db
```

---

## Rollback Scenarios and Solutions

### Scenario 1: Migration Fails with Constraint Violation

**Error Example**:
```
sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError) FOREIGN KEY constraint failed
```

**Solution**:

```bash
# Step 1: Rollback migration
cd backend
alembic downgrade -1

# Step 2: Check data consistency
sqlite3 data/vbrpg.db
sqlite> PRAGMA foreign_key_check;
sqlite> .exit

# Step 3: If inconsistencies found, restore from backup
cp data/backups/vbrpg_backup_<timestamp>.db data/vbrpg.db

# Step 4: Restart service
sudo systemctl restart vbrpg-backend
```

---

### Scenario 2: Service Won't Start After Migration

**Error Example**:
```
ImportError: cannot import name 'GameRoomParticipant' from 'src.db.models'
```

**Solution**:

```bash
# Step 1: Check if migration ran but code didn't deploy
alembic current  # Shows new version
git log --oneline -1  # Shows old code

# Step 2: Rollback migration to match code
alembic downgrade -1

# Step 3: Restart service
sudo systemctl restart vbrpg-backend

# Step 4: Re-run deployment with correct order
./scripts/deploy.sh
```

---

### Scenario 3: Data Loss After Migration

**Symptoms**:
- Rooms disappeared
- Players missing
- Game states corrupted

**Solution**:

```bash
# Step 1: IMMEDIATELY stop service to prevent further writes
sudo systemctl stop vbrpg-backend

# Step 2: Restore database from pre-migration backup
cd backend
mv data/vbrpg.db data/vbrpg_dataloss_$(date +%Y%m%d_%H%M%S).db
cp data/backups/vbrpg_backup_<timestamp>.db data/vbrpg.db

# Step 3: Verify data restoration
sqlite3 data/vbrpg.db
sqlite> SELECT COUNT(*) FROM game_rooms;
sqlite> SELECT COUNT(*) FROM players;
sqlite> .exit

# Step 4: DO NOT run migration again until bug is fixed
# Keep code on previous version

# Step 5: Restart service on old version
git checkout <previous_commit>
sudo systemctl start vbrpg-backend

# Step 6: Investigate migration script for data loss bug
# File: backend/alembic/versions/<migration_hash>_*.py
```

---

### Scenario 4: Performance Degradation After Deployment

**Symptoms**:
- Slow API responses (> 5 seconds)
- High CPU usage
- Database locks

**Solution**:

```bash
# Step 1: Check database indexes
sqlite3 backend/data/vbrpg.db
sqlite> .indexes
sqlite> EXPLAIN QUERY PLAN SELECT * FROM game_room_participants WHERE room_id = 1;
sqlite> .exit

# Step 2: If migration removed indexes, rollback
cd backend
alembic downgrade -1

# Step 3: Restart service
sudo systemctl restart vbrpg-backend

# Step 4: Monitor performance
curl -w "@curl-format.txt" http://localhost:8000/api/rooms/ABC123
```

**curl-format.txt** (for performance testing):
```
time_namelookup:  %{time_namelookup}\n
time_connect:     %{time_connect}\n
time_total:       %{time_total}\n
```

---

## Rollback Verification Checklist

After performing any rollback:

- [ ] **Service Health**: `curl http://localhost:8000/health` returns 200
- [ ] **Database Integrity**: `sqlite3 data/vbrpg.db "PRAGMA integrity_check;"`
- [ ] **Migration Version**: `alembic current` matches expected version
- [ ] **Core Functionality**:
  - [ ] Create room works
  - [ ] Join room works
  - [ ] Leave room works
  - [ ] Add/remove AI agents works (if applicable)
- [ ] **Data Verification**:
  - [ ] Existing rooms are accessible
  - [ ] Player accounts intact
  - [ ] Game sessions preserved
- [ ] **Performance**: API response times < 1 second
- [ ] **Logs Clean**: No errors in `journalctl -u vbrpg-backend -n 50`

---

## Prevention Best Practices

### Before Deployment

1. **Test Migrations Locally**:
   ```bash
   # Run migration on local dev database
   cd backend
   alembic upgrade head
   
   # Test rollback
   alembic downgrade -1
   alembic upgrade head
   ```

2. **Backup Database**:
   - Automatic: `BACKUP_DB=true ./scripts/deploy.sh`
   - Manual: `cp backend/data/vbrpg.db backend/data/backups/manual_backup_$(date +%Y%m%d_%H%M%S).db`

3. **Test on Staging**:
   ```bash
   ENVIRONMENT=staging ./scripts/deploy.sh
   # Run E2E tests
   cd frontend && npm run test:e2e
   ```

### During Deployment

1. **Monitor Logs**:
   ```bash
   # In separate terminal
   journalctl -u vbrpg-backend -f
   ```

2. **Health Checks**:
   ```bash
   watch -n 5 'curl -s http://localhost:8000/health | jq'
   ```

### After Deployment

1. **Smoke Tests**:
   ```bash
   ./scripts/smoke-tests.sh
   ```

2. **Performance Monitoring**:
   ```bash
   # Check response times
   for i in {1..10}; do
     curl -w "Time: %{time_total}s\n" http://localhost:8000/api/rooms/ABC123
     sleep 1
   done
   ```

---

## Emergency Contacts

| Role | Contact | Availability |
|------|---------|--------------|
| Lead Developer | (Add contact) | 24/7 |
| Database Admin | (Add contact) | Business hours |
| DevOps Engineer | (Add contact) | On-call |

---

## Rollback History

Track all rollbacks for audit and learning:

| Date | Version Rolled Back | Reason | Time to Recover | Notes |
|------|---------------------|--------|-----------------|-------|
| YYYY-MM-DD | v1.2.0 | Migration failure | 15 minutes | Foreign key constraint error |
| YYYY-MM-DD | v1.3.0 | Data loss detected | 10 minutes | Restored from backup |

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-11-09  
**Feature**: 002-room-join-management
