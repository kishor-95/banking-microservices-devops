# General Variables
variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "banking-microservices"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

# VPC Variables
variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "single_nat_gateway" {
  description = "Use single NAT gateway for cost optimization"
  type        = bool
  default     = true
}

variable "one_nat_gateway_per_az" {
  description = "Use one NAT gateway per AZ for high availability"
  type        = bool
  default     = false
}

# EKS Variables
variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "banking-eks-dev"
}

variable "cluster_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.29"
}

variable "node_instance_types" {
  description = "EKS node instance types"
  type        = list(string)
  default     = ["c7i-flex.large"]
}

variable "node_min_size" {
  description = "Minimum number of EKS nodes"
  type        = number
  default     = 1
}

variable "node_max_size" {
  description = "Maximum number of EKS nodes"
  type        = number
  default     = 3
}

variable "node_desired_size" {
  description = "Desired number of EKS nodes"
  type        = number
  default     = 2
}

# Bastion Variables
variable "bastion_instance_type" {
  description = "Bastion instance type"
  type        = string
  default     = "t3.small"
}

variable "ec2_key_name" {
  description = "EC2 key pair name for SSH access"
  type        = string
}

variable "allowed_ssh_cidr_blocks" {
  description = "CIDR blocks allowed to SSH to bastion"
  type        = list(string)
  # Default to no access - user must provide their IP
  default = []
}

# RDS Variables
variable "db_engine_version" {
  description = "PostgreSQL engine version"
  type        = string
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "Initial allocated storage in GB"
  type        = number
  default     = 20
}

variable "db_max_allocated_storage" {
  description = "Maximum allocated storage for autoscaling"
  type        = number
  default     = 50
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "bankapp"
}

variable "db_username" {
  description = "Master database username"
  type        = string
  default     = "dbadmin"
}

variable "db_backup_retention_period" {
  description = "Database backup retention period in days"
  type        = number
  default     = 7
}

variable "db_deletion_protection" {
  description = "Enable deletion protection for RDS"
  type        = bool
  default     = true
}

variable "db_skip_final_snapshot" {
  description = "Skip final snapshot on RDS deletion"
  type        = bool
  default     = false
}

variable "common_tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}
