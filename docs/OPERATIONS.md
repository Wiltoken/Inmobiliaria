# Operations Guide

## Daily Operations

### Health Check Verification

```bash
# Check all services
make health

# Expected output:
# API: OK
# Postgres: OK
# Redis: OK
```

### Review Logs

```bash
# All services
make logs

# API logs only
make logs-api

# Recent errors
docker compose -f docker-compose.prod.yml logs --since 1h --tail=500 | grep -i error

# Check for 5xx errors
docker compose -f docker-compose.prod.yml logs --tail=1000 | grep '"status":5'
```

### Verify Backups

```bash
# List recent backups
docker compose -f docker-compose.prod.yml exec postgres ls -lh /backups/

# Check backup size (should be > 0)
ls -lh /backups/inmobiliaria_*.sql.gz

# Test backup integrity
gunzip -c /backups/inmobiliaria_latest.sql.gz | head -20
```

## Weekly Operations

### Backup Verification

```bash
# Restore to test environment (never production!)
# 1. Create test database
docker compose -f docker-compose.prod.yml exec postgres psql -U inmuebles -c "CREATE DATABASE test_restore;"

# 2. Restore
docker compose -f docker-compose.prod.yml exec -T postgres \
  gunzip -c /backups/inmobiliaria_latest.sql.gz | \
  psql -U inmuebles -d test_restore

# 3. Verify
docker compose -f docker-compose.prod.yml exec postgres psql -U inmuebles -d test_restore -c "SELECT COUNT(*) FROM users;"
```

### Review Error Rates

```bash
# Parse logs for error patterns
docker compose -f docker-compose.prod.yml logs --tail=10000 | \
  grep -E '(ERROR|CRITICAL|Exception)' | \
  sort | uniq -c | sort -rn | head -20

# Check API response times
docker compose -f docker-compose.prod.yml logs api --since 24h | \
  grep 'request_id' | \
  jq '.duration' 2>/dev/null | \
  awk '{sum+=$1; count++} END {print "avg:", sum/count, "ms"}'
```

### Review Celery Task Failures

```bash
# Check Celery logs
make logs-celery

# Look for failed tasks
docker compose -f docker-compose.prod.yml logs celery-worker --since 7d | grep -i failure

# Check retry counts
docker compose -f docker-compose.prod.yml exec celery-worker \
  celery -A app.core.celery_app inspect failed
```

## Monthly Operations

### Rotate Secrets

```bash
# 1. Generate new SECRET_KEY
NEW_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(64))")

# 2. Update .env (add new key, keep old for rotation period)
# SECRET_KEY_NEW=<new_key>
# SECRET_KEY=<old_key>

# 3. Deploy with new key
make deploy

# 4. After verification, remove old key
# Remove SECRET_KEY_NEW, keep SECRET_KEY
```

### Dependency Update Review

```bash
# Check for outdated dependencies
pip list --outdated

# Review changelogs for breaking changes
# Update in pyproject.toml

# Rebuild and test
docker compose -f docker-compose.prod.yml build --pull api
```

### Disaster Recovery Test

```bash
# 1. Document current state
docker compose -f docker-compose.prod.yml ps

# 2. Simulate failure (optional)
# docker compose -f docker-compose.prod.yml stop postgres

# 3. Restore from backup
make restore FILE=<backup_file>

# 4. Verify functionality
make health
make test
```

## Runbooks

### Service Restart

```bash
# Single service
make restart-api
make restart-celery

# All services
make restart

# Check recovery
make health
```

### Database Restore

```bash
# 1. List available backups
docker compose -f docker-compose.prod.yml exec postgres ls -lh /backups/

# 2. Restore (interactive)
make restore

# 3. Or non-interactive (for automation)
docker compose -f docker-compose.prod.yml exec -T postgres \
  /backups/restore.sh /backups/inmobiliaria_20240115_030000.sql.gz

# 4. Verify
make health
```

### Scaling API Replicas

```bash
# Scale up
docker compose -f docker-compose.prod.yml up -d --scale api=5 api

# Scale down
docker compose -f docker-compose.prod.yml up -d --scale api=2 api

# Check status
docker compose -f docker-compose.prod.yml ps api
```

### SSL Certificate Renewal

```bash
# 1. Check certificate expiry
docker compose -f docker-compose.prod.yml exec nginx \
  sh -c "openssl s_client -connect localhost:443 -servername inmobiliaria.example.com 2>/dev/null | openssl x509 -noout -dates"

# 2. Renew (if using Let's Encrypt)
docker compose -f docker-compose.prod.yml run --rm certbot certbot renew

# 3. Reload nginx
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload

# 4. Verify
docker compose -f docker-compose.prod.yml exec nginx \
  sh -c "openssl s_client -connect localhost:443 2>/dev/null | openssl x509 -noout -dates"
```

### Redis Cache Flush (Emergency Only)

```bash
# WARNING: This will log out all users and reset rate limits
docker compose -f docker-compose.prod.yml exec redis redis-cli FLUSHALL

# Check logs for issues after flush
make logs
```

### PgBouncer Restart

```bash
# Restart PgBouncer
docker compose -f docker-compose.prod.yml restart pgbouncer

# Check connections
docker compose -f docker-compose.prod.yml exec pgbouncer \
  psql -h localhost -U inmuebles -d inmobiliaria_db -c "SHOW CLIENTS;"
```

### Celery Worker Restart

```bash
# Restart workers
docker compose -f docker-compose.prod.yml restart celery-worker

# Check task queue
docker compose -f docker-compose.prod.yml exec celery-worker \
  celery -A app.core.celery_app inspect active_queues

# Force restart (kill tasks and restart)
docker compose -f docker-compose.prod.yml kill celery-worker
docker compose -f docker-compose.prod.yml up -d celery-worker
```

## Monitoring Checklist

### Services Health

- [ ] API replicas running (check count)
- [ ] PostgreSQL healthy and accepting connections
- [ ] Redis healthy and responding to PING
- [ ] MinIO healthy
- [ ] Celery workers running and processing tasks
- [ ] Celery Beat scheduler running

### Resource Usage

- [ ] PostgreSQL connections < 80% of max
- [ ] Redis memory < 200MB (of 256MB allocated)
- [ ] API container CPU < 80% sustained
- [ ] Disk space > 20% free on all volumes

### Business Metrics

- [ ] Login success rate > 95%
- [ ] API response time p95 < 500ms
- [ ] No spike in 5xx errors
- [ ] Backup completion rate 100%

### Security

- [ ] No failed login attempts from suspicious IPs
- [ ] Audit logs being written
- [ ] SSL certificates valid

## Performance Tuning

### PostgreSQL

```sql
-- Check slow queries
SELECT query, calls, mean_time, total_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Check connection usage
SELECT count(*), state FROM pg_stat_activity GROUP BY state;

-- Check index usage
SELECT indexrelname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC;
```

### Redis

```bash
# Check memory usage
docker compose -f docker-compose.prod.yml exec redis redis-cli INFO memory

# Check hit rate
docker compose -f docker-compose.prod.yml exec redis redis-cli INFO stats

# Check key count by pattern
docker compose -f docker-compose.prod.yml exec redis redis-cli --scan --pattern "rate_limit:*" | wc -l
```

### API

```bash
# Check request latency
curl -w "@curl_format.txt" -o /dev/null -s http://localhost:8000/api/v1/properties/

# curl_format.txt:
# time_namelookup:  %{time_namelookup}\n
# time_connect:  %{time_connect}\n
# time_appconnect:  %{time_appconnect}\n
# time_pretransfer:  %{time_pretransfer}\n
# time_redirect:  %{time_redirect}\n
# time_starttransfer:  %{time_starttransfer}\n
# time_total:  %{time_total}\n
```

## Incident Response

### High API Latency

1. Check database latency: `make shell-postgres` then `\timing`
2. Check Redis latency: `make shell-redis` then `DEBUG SLEEP 0`
3. Review slow query logs
4. Scale up API replicas if needed
5. Check for DDoS/rate limit issues

### Database Connection Exhaustion

1. Check PgBouncer: `docker compose exec pgbouncer pgbouncer -c "show pools"`
2. Check active connections: `make shell-postgres` then `SELECT * FROM pg_stat_activity`
3. Restart PgBouncer if needed
4. Scale up `default_pool_size` if sustained

### Celery Task Backlog

1. Check queue depth: `docker compose exec celery-worker celery -A app.core.celery_app inspect stats`
2. Scale workers: `docker compose up -d --scale celery-worker=4`
3. Check for failed tasks: `docker compose logs celery-worker | grep "Task failed"`
4. Retry failed tasks if needed

## Backup Automation

### Cron Schedule (for external backup system)

```cron
# Daily backup at 2 AM UTC
0 2 * * * docker compose -f /path/to/docker-compose.prod.yml exec -T postgres /backups/backup.sh

# Weekly integrity check on Sunday at 3 AM
0 3 * * 0 docker compose -f /path/to/docker-compose.prod.yml exec -T postgres psql -U inmuebles -d inmobiliaria_db -c "SELECT 1;"

# Monthly offsite sync at 4 AM on 1st
0 4 1 * * aws s3 sync /backups s3://your-bucket/backups/ --delete
```

### Backup to S3

```bash
# Install AWS CLI in container
docker compose -f docker-compose.prod.yml exec -T postgres \
  sh -c "pip install awscli && aws s3 sync /backups s3://your-bucket/backups/"
```

## Log Aggregation

### Centralized Logging (Future)

Recommended: ELK Stack or Loki/Grafana

```yaml
# docker-compose.prod.yml add logspout
logspout:
  image: gliderlabs/logspout:latest
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
  command: syslog://loki:1514
  depends_on:
    - api
```
