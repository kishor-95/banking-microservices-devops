variable "vpc_id" {
  description = "VPC ID where security groups will be created"
  type        = string

  validation {
    condition     = can(regex("^vpc-", var.vpc_id))
    error_message = "VPC ID must start with 'vpc-'."
  }
}

variable "name_prefix" {
  description = "Prefix for security group names"
  type        = string

  validation {
    condition     = length(var.name_prefix) > 0 && length(var.name_prefix) <= 20
    error_message = "Name prefix must be 1-20 characters."
  }
}

variable "cluster_name" {
  description = "EKS cluster name for tagging"
  type        = string
}

variable "eks_node_security_group_id" {
  description = "EKS node security group ID (from EKS module)"
  type        = string

  validation {
    condition     = can(regex("^sg-", var.eks_node_security_group_id))
    error_message = "Security group ID must start with 'sg-'."
  }
}

variable "enable_bastion" {
  description = "Enable bastion security group (for SSH access via Systems Manager)"
  type        = bool
  default     = false
}

variable "common_tags" {
  description = "Common tags to apply to all security groups"
  type        = map(string)
  default     = {}
}
