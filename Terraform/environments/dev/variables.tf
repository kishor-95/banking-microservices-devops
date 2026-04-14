# =============================================================================
# GENERAL VARIABLES
# =============================================================================

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "ap-south-1"

  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]{1}$", var.aws_region))
    error_message = "AWS region must be a valid AWS region (e.g., ap-south-1)."
  }
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "project_name" {
  description = "Project name - used for resource naming"
  type        = string
  default     = "banking-microservices"

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name)) && length(var.project_name) <= 20
    error_message = "Project name must be lowercase alphanumeric with hyphens, max 20 chars."
  }
}

# =============================================================================
# VPC VARIABLES
# =============================================================================

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "VPC CIDR must be a valid CIDR block."
  }
}

variable "availability_zones_count" {
  description = "Number of availability zones to use (2 or 3)"
  type        = number
  default     = 2

  validation {
    condition     = contains([2, 3], var.availability_zones_count)
    error_message = "Must use 2 or 3 availability zones."
  }
}

variable "single_nat_gateway" {
  description = "Use single NAT gateway (cost optimization - not for production)"
  type        = bool
  default     = true
}

variable "enable_nat_gateway" {
  description = "Enable NAT gateway for private subnet internet access"
  type        = bool
  default     = true
}

# =============================================================================
# EKS CLUSTER VARIABLES
# =============================================================================

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "banking-eks-dev"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,30}[a-z0-9]$", var.cluster_name))
    error_message = "Cluster name must start with lowercase letter, contain only lowercase letters, numbers, and hyphens."
  }
}

variable "cluster_version" {
  description = "Kubernetes version (must be a valid EKS version)"
  type        = string
  default     = "1.29"

  validation {
    condition     = can(regex("^1\\.[0-9]{2}$", var.cluster_version))
    error_message = "Cluster version must be in format 1.XX (e.g., 1.29)."
  }
}

variable "node_instance_types" {
  description = "EC2 instance types for EKS nodes (should be compute optimized)"
  type        = list(string)
  default     = ["t3.large"]

  validation {
    condition     = length(var.node_instance_types) > 0
    error_message = "At least one instance type must be specified."
  }
}

variable "node_min_size" {
  description = "Minimum number of EKS nodes"
  type        = number
  default     = 2

  validation {
    condition     = var.node_min_size >= 1
    error_message = "Minimum node size must be at least 1."
  }
}

variable "node_max_size" {
  description = "Maximum number of EKS nodes"
  type        = number
  default     = 5

  validation {
    condition     = var.node_max_size >= var.node_min_size
    error_message = "Maximum node size must be >= minimum node size."
  }
}

variable "node_desired_size" {
  description = "Desired number of EKS nodes"
  type        = number
  default     = 2

  validation {
    condition     = var.node_desired_size >= var.node_min_size && var.node_desired_size <= var.node_max_size
    error_message = "Desired size must be between min and max size."
  }
}

variable "enable_cluster_autoscaling" {
  description = "Enable Kubernetes Cluster Autoscaler"
  type        = bool
  default     = true
}

# =============================================================================
# RDS DATABASE VARIABLES
# =============================================================================

variable "rds_engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "17.6"
}

variable "rds_instance_class" {
  description = "RDS instance class (not micro for production)"
  type        = string
  default     = "db.t3.small"

  #   validation {
  #     condition     = !contains(["db.t2.micro", "db.t3.micro"], var.rds_instance_class)
  #     error_message = "Micro instances not allowed for banking applications."
  #   }
}

variable "rds_allocated_storage" {
  description = "Initial allocated storage in GB"
  type        = number
  default     = 20

  validation {
    condition     = var.rds_allocated_storage >= 20 && var.rds_allocated_storage <= 65536
    error_message = "RDS storage must be between 20 and 65536 GB."
  }
}

variable "rds_max_allocated_storage" {
  description = "Maximum allocated storage for autoscaling (auto-scaling disabled if null)"
  type        = number
  default     = 100

  validation {
    condition     = var.rds_max_allocated_storage >= var.rds_allocated_storage
    error_message = "Max storage must be >= allocated storage."
  }
}

variable "rds_database_name" {
  description = "Initial database name"
  type        = string
  default     = "bankapp"

  validation {
    condition     = can(regex("^[a-z][a-z0-9_]*$", var.rds_database_name))
    error_message = "Database name must start with letter, contain only lowercase letters, numbers, underscores."
  }
}

variable "rds_master_username" {
  description = "Master database username"
  type        = string
  default     = "dbadmin"

  validation {
    condition     = can(regex("^[a-z][a-z0-9_]*$", var.rds_master_username))
    error_message = "Username must start with letter, contain only lowercase letters, numbers, underscores."
  }
}

variable "rds_backup_retention_days" {
  description = "Database backup retention period (1-35 days)"
  type        = number
  default     = 7

  validation {
    condition     = var.rds_backup_retention_days >= 1 && var.rds_backup_retention_days <= 35
    error_message = "Backup retention must be between 1 and 35 days."
  }
}

variable "rds_multi_az" {
  description = "Enable Multi-AZ deployment (critical for production)"
  type        = bool
  default     = false # Set to true for production/staging

  # Note: No validation - user must consciously choose
}

variable "rds_storage_encrypted" {
  description = "Enable RDS storage encryption"
  type        = bool
  default     = true
}

variable "rds_deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = true
}

variable "rds_skip_final_snapshot" {
  description = "Skip final snapshot on deletion (dev only)"
  type        = bool
  default     = true
}

# =============================================================================
# AWS LOAD BALANCER CONTROLLER
# =============================================================================

variable "aws_load_balancer_controller_chart_version" {
  description = "AWS Load Balancer Controller Helm chart version"
  type        = string
  default     = "2.7.0"
}

variable "enable_aws_load_balancer_controller" {
  description = "Deploy AWS Load Balancer Controller"
  type        = bool
  default     = true
}

# =============================================================================
# TAGS
# =============================================================================

variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}
