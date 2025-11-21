terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.20"
    }
  }
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "database_url" {
  description = "PostgreSQL database URL"
  type        = string
  sensitive   = true
}

variable "redis_url" {
  description = "Redis connection URL"
  type        = string
  sensitive   = true
}

variable "secret_key" {
  description = "Secret key for cryptography"
  type        = string
  sensitive   = true
}

provider "aws" {
  region = var.region
}

# EKS Cluster (if using EKS)
# data "aws_eks_cluster" "cluster" {
#   name = "bgp-detector-cluster"
# }

# data "aws_eks_cluster_auth" "cluster" {
#   name = "bgp-detector-cluster"
# }

# provider "kubernetes" {
#   host                   = data.aws_eks_cluster.cluster.endpoint
#   cluster_ca_certificate = base64decode(data.aws_eks_cluster.cluster.certificate_authority[0].data)
#   token                  = data.aws_eks_cluster_auth.cluster.token
# }

# S3 bucket for model storage
resource "aws_s3_bucket" "models" {
  bucket = "bgp-detector-models-${var.environment}"

  tags = {
    Name        = "BGP Detector Models"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "models" {
  bucket = aws_s3_bucket.models.id
  versioning_configuration {
    status = "Enabled"
  }
}

# RDS PostgreSQL instance
resource "aws_db_instance" "postgres" {
  identifier             = "bgp-detector-db-${var.environment}"
  engine                 = "postgres"
  engine_version         = "15.4"
  instance_class         = "db.t3.medium"
  allocated_storage      = 100
  storage_encrypted      = true
  db_name                = "bgp_orchestrator"
  username               = "bgp_user"
  password               = var.database_url # In production, use secrets manager
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
  backup_retention_period = 7
  skip_final_snapshot    = false
  final_snapshot_identifier = "bgp-detector-final-snapshot-${var.environment}"

  tags = {
    Name        = "BGP Detector Database"
    Environment = var.environment
  }
}

# ElastiCache Redis
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "bgp-detector-redis-${var.environment}"
  description                = "Redis for BGP Detector"
  node_type                  = "cache.t3.medium"
  port                       = 6379
  parameter_group_name       = "default.redis7"
  num_cache_clusters         = 2
  automatic_failover_enabled = true
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true

  tags = {
    Name        = "BGP Detector Redis"
    Environment = var.environment
  }
}

# Security Groups
resource "aws_security_group" "rds" {
  name        = "bgp-detector-rds-sg-${var.environment}"
  description = "Security group for RDS PostgreSQL"

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "BGP Detector RDS SG"
    Environment = var.environment
  }
}

resource "aws_db_subnet_group" "main" {
  name       = "bgp-detector-db-subnet-${var.environment}"
  subnet_ids = [] # Add your subnet IDs here

  tags = {
    Name        = "BGP Detector DB Subnet Group"
    Environment = var.environment
  }
}

# Outputs
output "database_endpoint" {
  value       = aws_db_instance.postgres.endpoint
  description = "RDS PostgreSQL endpoint"
  sensitive   = true
}

output "redis_endpoint" {
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
  description = "ElastiCache Redis endpoint"
  sensitive   = true
}

output "models_bucket" {
  value       = aws_s3_bucket.models.bucket
  description = "S3 bucket for model storage"
}

