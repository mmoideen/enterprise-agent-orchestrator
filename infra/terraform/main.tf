terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# VPC and Networking
module "vpc" {
  source = "./modules/vpc"

  environment = var.environment
  vpc_cidr    = var.vpc_cidr
}

# RDS PostgreSQL
module "database" {
  source = "./modules/rds"

  environment         = var.environment
  vpc_id              = module.vpc.vpc_id
  private_subnet_ids  = module.vpc.private_subnet_ids
  database_name       = "enterprise_agents"
  database_username   = var.database_username
  database_password   = var.database_password
  instance_class      = var.database_instance_class
}

# ElastiCache Redis
module "cache" {
  source = "./modules/elasticache"

  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  node_type          = var.redis_node_type
}

# ECS Cluster
module "ecs" {
  source = "./modules/ecs"

  environment           = var.environment
  vpc_id                = module.vpc.vpc_id
  public_subnet_ids     = module.vpc.public_subnet_ids
  private_subnet_ids    = module.vpc.private_subnet_ids
  database_url          = module.database.connection_string
  redis_url             = module.cache.connection_string
  orchestrator_image    = var.orchestrator_image
  worker_image          = var.worker_image
  secret_key            = var.secret_key
}

# Application Load Balancer
module "alb" {
  source = "./modules/alb"

  environment       = var.environment
  vpc_id            = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
  target_group_arn  = module.ecs.orchestrator_target_group_arn
}
