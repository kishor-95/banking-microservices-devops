variable "vpc_name" {
  description = "Name of the VPC"
  type        = string
  
  validation {
    condition     = length(var.vpc_name) > 0 && length(var.vpc_name) <= 32
    error_message = "VPC name must be between 1 and 32 characters."
  }
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  
  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "VPC CIDR must be a valid CIDR block."
  }
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  
  validation {
    condition     = length(var.availability_zones) >= 2 && length(var.availability_zones) <= 3
    error_message = "Must specify 2 or 3 availability zones."
  }
}

variable "availability_zones_count" {
  description = "Count of availability zones"
  type        = number
  
  validation {
    condition     = var.availability_zones_count >= 2 && var.availability_zones_count <= 3
    error_message = "Must use 2 or 3 availability zones."
  }
}

variable "single_nat_gateway" {
  description = "Use single NAT gateway (cost optimization, creates SPOF)"
  type        = bool
  default     = true
}

variable "enable_nat_gateway" {
  description = "Enable NAT gateway for private subnet internet access"
  type        = bool
  default     = true
}

variable "cluster_name" {
  description = "EKS cluster name for subnet tagging"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}
