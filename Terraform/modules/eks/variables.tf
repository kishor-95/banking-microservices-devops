variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,30}[a-z0-9]$", var.cluster_name))
    error_message = "Cluster name must start with lowercase letter, max 32 chars, alphanumeric and hyphens only."
  }
}

variable "cluster_version" {
  description = "Kubernetes version to use for the EKS cluster (1.XX format)"
  type        = string

  validation {
    condition     = can(regex("^1\\.[0-9]{2}$", var.cluster_version))
    error_message = "Cluster version must be in format 1.XX (e.g., 1.29)."
  }
}

variable "vpc_id" {
  description = "VPC ID where EKS cluster will be deployed"
  type        = string

  validation {
    condition     = can(regex("^vpc-", var.vpc_id))
    error_message = "VPC ID must start with 'vpc-'."
  }
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for EKS nodes"
  type        = list(string)

  validation {
    condition     = length(var.private_subnet_ids) >= 2
    error_message = "At least 2 private subnets required for HA."
  }
}

variable "node_instance_types" {
  description = "List of instance types for EKS managed node group"
  type        = list(string)

  validation {
    condition     = length(var.node_instance_types) > 0
    error_message = "At least one instance type must be specified."
  }
}

variable "node_min_size" {
  description = "Minimum number of worker nodes"
  type        = number

  validation {
    condition     = var.node_min_size >= 1
    error_message = "Minimum node size must be at least 1."
  }
}

variable "node_max_size" {
  description = "Maximum number of worker nodes"
  type        = number

  validation {
    condition     = var.node_max_size >= var.node_min_size
    error_message = "Maximum node size must be >= minimum node size."
  }
}

variable "node_desired_size" {
  description = "Desired number of worker nodes"
  type        = number

  validation {
    condition     = var.node_desired_size >= var.node_min_size && var.node_desired_size <= var.node_max_size
    error_message = "Desired size must be between min and max size."
  }
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "common_tags" {
  description = "Common tags to apply to all EKS resources"
  type        = map(string)
  default     = {}
}
