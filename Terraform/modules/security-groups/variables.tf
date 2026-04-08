variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "name_prefix" {
  description = "Prefix for security group names"
  type        = string
}

variable "allowed_ssh_cidr_blocks" {
  description = "CIDR blocks allowed to SSH to bastion"
  type        = list(string)
}

variable "eks_node_security_group_id" {
  description = "EKS node security group ID"
  type        = string
  default     = ""
}

variable "common_tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}

variable "eks_cluster_security_group_id" {
  description = "EKS cluster SG ID"
  type        = string
}