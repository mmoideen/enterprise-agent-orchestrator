# Terraform Infrastructure

This directory contains Terraform modules for deploying the Enterprise Agent Orchestrator to AWS.

## Architecture

The infrastructure includes:

- **VPC**: Isolated network with public and private subnets across 2 availability zones
- **RDS PostgreSQL**: Managed database for agent registry and audit logs
- **ElastiCache Redis**: In-memory cache for session storage and distributed locking
- **ECS Fargate**: Serverless container orchestration for API and worker services
- **Application Load Balancer**: HTTP(S) load balancing with health checks
- **CloudWatch**: Centralized logging and monitoring

## Prerequisites

- Terraform >= 1.5
- AWS CLI configured with appropriate credentials
- Docker images pushed to ECR or Docker Hub

## Usage

1. Initialize Terraform:

```bash
cd infra/terraform
terraform init
```

2. Create a terraform.tfvars file:

```hcl
environment          = "production"
database_username    = "admin"
database_password    = "CHANGE_ME"
orchestrator_image   = "your-registry/orchestrator:latest"
worker_image         = "your-registry/worker:latest"
secret_key           = "CHANGE_ME"
```

3. Plan the deployment:

```bash
terraform plan
```

4. Apply the configuration:

```bash
terraform apply
```

## Security Considerations

- All sensitive resources (database, cache) are deployed in private subnets
- Security groups restrict access to necessary ports only
- Database credentials stored in AWS Secrets Manager (in production implementation)
- TLS termination at the load balancer
- IAM roles follow least privilege principle

## Cost Optimization

For development/staging environments, consider:

- Using smaller instance types (db.t3.micro, cache.t3.micro)
- Single AZ deployment
- Reducing ECS task count
- Using on-demand pricing instead of reserved instances

## Modules

- `vpc/`: Network infrastructure
- `rds/`: PostgreSQL database
- `elasticache/`: Redis cache
- `ecs/`: Container orchestration
- `alb/`: Load balancing

Each module is self-contained and can be used independently.
