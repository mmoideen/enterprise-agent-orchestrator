# Production Deployment Guide

This guide covers deploying the Enterprise Agent Orchestrator to production environments.

## Deployment Options

We support three deployment models:

1. **AWS (Recommended):** Fully managed using ECS, RDS, ElastiCache
2. **Kubernetes:** Self-managed on any cloud or on-premise
3. **Docker Compose:** Small-scale deployments

This guide focuses on AWS deployment using Terraform.

## Prerequisites

- AWS account with appropriate permissions
- AWS CLI configured (`aws configure`)
- Terraform >= 1.5 installed
- Docker images built and pushed to ECR

## Pre-Deployment Checklist

### 1. Build and Push Docker Images

```bash
# Authenticate with ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build images
docker build -f infra/docker/Dockerfile.orchestrator -t orchestrator:latest .
docker build -f infra/docker/Dockerfile.worker -t worker:latest .

# Tag images
docker tag orchestrator:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/orchestrator:latest
docker tag worker:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/worker:latest

# Push images
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/orchestrator:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/worker:latest
```

### 2. Create Secrets

Store sensitive values in AWS Secrets Manager:

```bash
aws secretsmanager create-secret \
  --name enterprise-agents/database-password \
  --secret-string "STRONG_RANDOM_PASSWORD"

aws secretsmanager create-secret \
  --name enterprise-agents/secret-key \
  --secret-string "STRONG_RANDOM_JWT_SECRET"
```

### 3. Configure Terraform Variables

Create `infra/terraform/terraform.tfvars`:

```hcl
environment          = "production"
aws_region           = "us-east-1"

# Database
database_username    = "admin"
database_password    = "RETRIEVE_FROM_SECRETS_MANAGER"
database_instance_class = "db.r6g.large"

# Cache
redis_node_type      = "cache.r6g.large"

# Container Images
orchestrator_image   = "<account-id>.dkr.ecr.us-east-1.amazonaws.com/orchestrator:latest"
worker_image         = "<account-id>.dkr.ecr.us-east-1.amazonaws.com/worker:latest"

# Security
secret_key           = "RETRIEVE_FROM_SECRETS_MANAGER"
```

## Deployment Steps

### 1. Initialize Terraform

```bash
cd infra/terraform
terraform init
```

### 2. Plan Deployment

Review the infrastructure changes:

```bash
terraform plan -out=tfplan
```

Expected resources:
- VPC with 6 subnets (3 public, 3 private)
- RDS PostgreSQL instance
- ElastiCache Redis cluster
- ECS cluster with Fargate tasks
- Application Load Balancer
- Security groups and IAM roles

### 3. Apply Configuration

```bash
terraform apply tfplan
```

Deployment time: ~15 minutes

### 4. Retrieve Outputs

```bash
terraform output alb_dns_name
```

This is your API endpoint. Configure DNS to point to this load balancer.

### 5. Run Database Migrations

From a bastion host or using ECS Exec:

```bash
alembic upgrade head
```

### 6. Verify Deployment

Test health endpoint:

```bash
curl https://your-domain.com/health
```

Expected response:
```json
{"status": "healthy"}
```

## Post-Deployment Configuration

### 1. Set Up DNS

Create a CNAME record pointing to the ALB DNS name:

```
api.yourcompany.com -> <alb-dns-name>
```

### 2. Configure TLS Certificate

Use AWS Certificate Manager:

```bash
aws acm request-certificate \
  --domain-name api.yourcompany.com \
  --validation-method DNS
```

Update ALB listener to use HTTPS with the certificate.

### 3. Configure Monitoring

Enable CloudWatch alarms:

```bash
# API error rate
aws cloudwatch put-metric-alarm \
  --alarm-name enterprise-agents-api-errors \
  --metric-name 5XXError \
  --namespace AWS/ApplicationELB \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold

# Database CPU
aws cloudwatch put-metric-alarm \
  --alarm-name enterprise-agents-db-cpu \
  --metric-name CPUUtilization \
  --namespace AWS/RDS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold
```

### 4. Configure Log Aggregation

Logs are automatically sent to CloudWatch. Set up log retention:

```bash
aws logs put-retention-policy \
  --log-group-name /ecs/enterprise-agents-orchestrator \
  --retention-in-days 30
```

### 5. Seed Initial Data

Create the first admin user:

```bash
# SSH to ECS task or use ECS Exec
python scripts/create_admin_user.py --email admin@yourcompany.com
```

## Security Hardening

### 1. Network Security

- All databases in private subnets (no internet access)
- Security groups allow only necessary ports
- NACLs provide additional network layer protection

### 2. Secrets Management

- Rotate database password quarterly:
  ```bash
  aws secretsmanager rotate-secret \
    --secret-id enterprise-agents/database-password
  ```

### 3. IAM Roles

- ECS tasks use least-privilege IAM roles
- Separate roles for orchestrator and worker
- No hardcoded credentials in code

### 4. Encryption

- RDS encryption at rest enabled
- ElastiCache encryption in transit enabled
- S3 buckets (if used) encrypted with KMS

## Scaling Configuration

### Horizontal Scaling

Auto-scale ECS tasks based on CPU:

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --scalable-dimension ecs:service:DesiredCount \
  --resource-id service/<cluster>/<service> \
  --min-capacity 2 \
  --max-capacity 10

aws application-autoscaling put-scaling-policy \
  --policy-name cpu-scaling \
  --service-namespace ecs \
  --scalable-dimension ecs:service:DesiredCount \
  --resource-id service/<cluster>/<service> \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration file://scaling-policy.json
```

### Vertical Scaling

Increase task CPU/memory in ECS task definition or upgrade RDS instance class.

## Backup and Recovery

### Database Backups

RDS automated backups enabled by default:
- Retention period: 7 days
- Backup window: 03:00-04:00 UTC
- Maintenance window: Sun 04:00-05:00 UTC

Manual snapshot:

```bash
aws rds create-db-snapshot \
  --db-instance-identifier enterprise-agents-db \
  --db-snapshot-identifier enterprise-agents-snapshot-$(date +%Y%m%d)
```

### Disaster Recovery

Recovery Time Objective (RTO): 1 hour
Recovery Point Objective (RPO): 5 minutes

Restore from snapshot:

```bash
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier enterprise-agents-db-restored \
  --db-snapshot-identifier <snapshot-id>
```

## Maintenance Windows

Schedule maintenance during low-traffic periods:

1. Update task definitions with new image tags
2. Deploy using rolling update (zero downtime)
3. Monitor CloudWatch metrics for anomalies
4. Rollback if error rate increases

## Monitoring and Alerting

Key metrics to monitor:

- **API Latency:** p95 < 500ms
- **Error Rate:** < 1%
- **Database Connections:** < 80% of max
- **Cache Hit Rate:** > 80%
- **Workflow Failures:** < 5%

Set up PagerDuty or similar for critical alerts.

## Troubleshooting

### High API Latency

1. Check database performance metrics
2. Review slow query logs
3. Verify cache hit rate
4. Scale ECS tasks horizontally

### Database Connection Exhaustion

1. Check for connection leaks in application
2. Increase RDS instance size
3. Reduce connection pool size per task

### Temporal Workflow Failures

1. Check worker task logs in CloudWatch
2. Verify workflow history in Temporal UI
3. Review workflow retry policies

## Rollback Procedure

If deployment issues occur:

```bash
# Revert to previous task definition
aws ecs update-service \
  --cluster enterprise-agents \
  --service orchestrator \
  --task-definition orchestrator:PREVIOUS_VERSION

# Rollback database migration
alembic downgrade -1
```

## Cost Optimization

Production costs (estimated):

- **RDS (db.r6g.large):** $200/month
- **ElastiCache (cache.r6g.large):** $150/month
- **ECS Fargate (2 tasks):** $100/month
- **ALB:** $20/month
- **Data Transfer:** $50/month

**Total:** ~$520/month

Reduce costs:
- Use reserved instances for predictable workloads
- Right-size instances based on actual usage
- Use spot instances for non-critical workers

## Compliance

This deployment architecture supports:

- **SOX:** Audit logs retained for 7 years
- **GDPR:** Encryption at rest and in transit, data deletion workflows
- **HIPAA:** BAA with AWS, encrypted storage, access logs

## Next Steps

- Set up CI/CD pipeline for automated deployments
- Configure blue/green deployments for zero-downtime updates
- Implement automated testing in staging environment
- Review [Incident Response](./incident-response.md) procedures
