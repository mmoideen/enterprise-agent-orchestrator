# Incident Response Runbook

This runbook provides procedures for handling common incidents in the Enterprise Agent Orchestrator.

## Incident Classification

### Severity Levels

- **SEV-1 (Critical):** Complete service outage, data loss risk
- **SEV-2 (High):** Partial outage, degraded performance
- **SEV-3 (Medium):** Non-critical feature broken, workaround available
- **SEV-4 (Low):** Minor issue, no user impact

### Response Times

| Severity | Acknowledgment | Resolution Target |
|----------|---------------|-------------------|
| SEV-1    | 15 minutes    | 4 hours           |
| SEV-2    | 1 hour        | 24 hours          |
| SEV-3    | 4 hours       | 1 week            |
| SEV-4    | 1 business day| 1 month           |

## Common Incidents

### 1. API Service Down

**Symptoms:**
- Health check returning 503
- No response from API endpoints
- ALB showing all targets unhealthy

**Diagnosis:**

```bash
# Check ECS task status
aws ecs list-tasks --cluster enterprise-agents --service-name orchestrator

# View task logs
aws logs tail /ecs/enterprise-agents-orchestrator --follow

# Check database connectivity
aws rds describe-db-instances --db-instance-identifier enterprise-agents-db
```

**Common Causes:**
- Database connection pool exhausted
- Out of memory errors
- Failed database migration
- AWS service disruption

**Resolution:**

```bash
# Restart ECS tasks
aws ecs update-service --cluster enterprise-agents --service orchestrator --force-new-deployment

# If database migration failed, rollback
alembic downgrade -1

# If out of memory, scale up task memory
aws ecs update-service --cluster enterprise-agents --service orchestrator --task-definition orchestrator:NEW_VERSION
```

**Prevention:**
- Implement connection pooling limits
- Set up memory monitoring alerts
- Test migrations in staging first

### 2. Agent Deployment Failures

**Symptoms:**
- Deployments stuck in PENDING or RUNNING state
- Temporal workflows showing errors
- Rollback workflows not completing

**Diagnosis:**

```bash
# Check Temporal workflow status
# Via Temporal UI: http://temporal-ui:8080

# Check worker logs
docker logs enterprise-agents-worker

# Query deployment status
curl -X GET "http://api/deployments?status=FAILED"
```

**Common Causes:**
- Temporal worker not running
- Activity timeout exceeded
- Invalid agent configuration
- Resource quota exceeded

**Resolution:**

```bash
# Restart Temporal worker
docker restart enterprise-agents-worker

# Manually trigger rollback
curl -X POST "http://api/deployments/{deployment_id}/rollback" \
  -H "Authorization: Bearer $TOKEN"

# Increase activity timeout in workflow definition
# Edit apps/worker/workflows/agent_lifecycle.py
```

**Prevention:**
- Monitor worker health continuously
- Implement workflow timeout alerts
- Validate configurations before deployment

### 3. Database Performance Degradation

**Symptoms:**
- API response times > 2 seconds
- Database CPU > 80%
- Connection pool warnings in logs

**Diagnosis:**

```bash
# Check RDS performance metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=enterprise-agents-db \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average

# Identify slow queries
SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;
```

**Common Causes:**
- Missing indexes on frequently queried columns
- Long-running queries without pagination
- Table bloat from deletes
- Insufficient RDS instance size

**Resolution:**

```bash
# Add missing index (example)
CREATE INDEX idx_agent_status_owner ON agent(status, owner_id);

# Terminate long-running queries
SELECT pg_terminate_backend(pid) FROM pg_stat_activity
WHERE state = 'active' AND query_start < NOW() - INTERVAL '5 minutes';

# Scale up RDS instance (requires downtime)
aws rds modify-db-instance \
  --db-instance-identifier enterprise-agents-db \
  --db-instance-class db.r6g.xlarge \
  --apply-immediately
```

**Prevention:**
- Regular VACUUM and ANALYZE
- Query performance testing in staging
- Implement query timeout limits

### 4. Redis Cache Failures

**Symptoms:**
- API latency increased
- Cache miss rate > 50%
- Redis connection errors

**Diagnosis:**

```bash
# Check ElastiCache metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ElastiCache \
  --metric-name CacheMisses \
  --dimensions Name=CacheClusterId,Value=enterprise-agents-cache

# Connect to Redis
redis-cli -h <cache-endpoint>
INFO stats
```

**Common Causes:**
- Cache eviction due to memory pressure
- Network connectivity issues
- Redis process crash
- Key expiration too aggressive

**Resolution:**

```bash
# Flush cache (forces rebuild from database)
redis-cli FLUSHALL

# Scale up cache node type
aws elasticache modify-cache-cluster \
  --cache-cluster-id enterprise-agents-cache \
  --cache-node-type cache.r6g.xlarge

# Increase memory reservation
# Update ElastiCache parameter group
```

**Prevention:**
- Monitor cache memory usage
- Implement cache warming strategy
- Set appropriate TTL values

### 5. Temporal Workflow Stuck

**Symptoms:**
- Workflows not progressing
- Activities timing out
- Workflow history growing unbounded

**Diagnosis:**

Access Temporal UI: http://temporal-ui:8080

- Check workflow status
- Review activity history
- Examine worker logs

**Common Causes:**
- Worker crashed mid-execution
- Activity implementation hanging
- Workflow state corruption
- Resource deadlock

**Resolution:**

```bash
# Terminate stuck workflow
tctl workflow terminate --workflow_id <workflow-id> --reason "Manual intervention"

# Restart worker with clean state
docker restart enterprise-agents-worker

# Re-trigger deployment with new workflow
curl -X POST "http://api/deployments" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"agent_id": "...", "environment": "production"}'
```

**Prevention:**
- Implement workflow heartbeats
- Set reasonable activity timeouts
- Monitor workflow queue depth

### 6. PII Data Leak

**Symptoms:**
- PII detected in logs
- Audit alerts for unauthorized data access
- User reports sensitive data exposure

**Diagnosis:**

```bash
# Search audit logs for PII access
SELECT * FROM auditlog
WHERE event_type = 'pii_detected'
AND timestamp > NOW() - INTERVAL '24 hours';

# Identify affected agents
SELECT DISTINCT agent_id FROM datalineage
WHERE data_classification = 'restricted'
AND timestamp > NOW() - INTERVAL '24 hours';
```

**Immediate Actions:**

1. **Suspend affected agents:**
```bash
curl -X PATCH "http://api/agents/{agent_id}" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"status": "SUSPENDED"}'
```

2. **Notify security team:** Follow internal breach notification protocol

3. **Preserve evidence:** Take database snapshots for forensic analysis

4. **Assess scope:** Determine which data was exposed and to whom

**Resolution:**

```bash
# Enable PII redaction for agent
# Update agent configuration
{
  "pii_detection_enabled": true,
  "redact_pii": true,
  "require_pii_approval": true
}

# Audit all agent outputs
python scripts/audit_pii_exposure.py --agent-id <agent-id> --start-date <date>

# Update policies to prevent recurrence
# Add stricter PII access policies
```

**Prevention:**
- Mandatory PII detection for all agents
- Regular security audits
- Least-privilege data access
- Employee training on PII handling

## Rollback Procedures

### Application Rollback

```bash
# Identify previous working version
aws ecs describe-task-definition --task-definition orchestrator

# Rollback to previous revision
aws ecs update-service \
  --cluster enterprise-agents \
  --service orchestrator \
  --task-definition orchestrator:PREVIOUS_REVISION
```

### Database Rollback

```bash
# Check current migration version
alembic current

# Rollback one migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade <revision>
```

### Agent Deployment Rollback

Rollback is automatic via Temporal workflow compensation. Manual rollback:

```bash
curl -X POST "http://api/deployments/{deployment_id}/rollback" \
  -H "Authorization: Bearer $TOKEN"
```

## Communication Templates

### Incident Notification

**Subject:** [SEV-X] Enterprise Agent Orchestrator Incident

**Body:**
```
Incident ID: INC-YYYYMMDD-NNN
Severity: SEV-X
Status: Investigating | Identified | Resolved
Impact: [Brief description of user impact]

Timeline:
- HH:MM - Incident detected
- HH:MM - Investigation started
- HH:MM - Root cause identified
- HH:MM - Fix deployed
- HH:MM - Incident resolved

Root Cause: [Brief explanation]

Next Steps:
- [Preventive measures]
- [Follow-up tasks]

Incident Commander: [Name]
```

## Post-Incident Review

Within 48 hours of resolution:

1. **Create incident report:** Document timeline, root cause, impact
2. **Identify action items:** Preventive measures and improvements
3. **Update runbooks:** Add learnings to this document
4. **Share learnings:** Team retrospective meeting

## Escalation Contacts

| Role                  | Contact              | Escalation Time |
|-----------------------|---------------------|-----------------|
| On-Call Engineer      | PagerDuty           | Immediate       |
| Engineering Manager   | Slack @eng-manager  | 30 minutes      |
| VP Engineering        | Phone +1-XXX-XXX    | 2 hours (SEV-1) |
| Security Team         | security@company    | Immediate (PII) |

## Monitoring Dashboards

- **CloudWatch:** AWS Console > CloudWatch > Dashboards > enterprise-agents
- **Temporal UI:** http://temporal-ui:8080
- **Application Metrics:** http://grafana:3000 (if deployed)

## Additional Resources

- [AWS Support Center](https://console.aws.amazon.com/support/)
- [Temporal Community Slack](https://temporal.io/slack)
- [Internal Wiki: Incident Response](https://wiki.company.com/incident-response)
