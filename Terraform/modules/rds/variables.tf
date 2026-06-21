variable "identifier" {
  description = "RDS instance identifier"
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]*$", var.identifier)) && length(var.identifier) <= 63
    error_message = "Identifier must start with letter, contain only lowercase letters/numbers/hyphens, max 63 chars."
  }
}

variable "engine_version" {
  description = "PostgreSQL engine version (e.g., 17.6)"
  type        = string

  validation {
    condition     = can(regex("^[0-9]+\\.[0-9]+$", var.engine_version))
    error_message = "Engine version must be in X.Y format (e.g., 17.6)."
  }
}

variable "instance_class" {
  description = "RDS instance class (db.t3.small, db.r6i.large, etc.)"
  type        = string

  # validation {
  #   condition     = !contains(["db.t2.micro", "db.t3.micro"], var.instance_class)
  #   error_message = "Micro instances not allowed - use at least db.t3.small for production."
  # }
}

variable "database_name" {
  description = "Initial database name"
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9_]*$", var.database_name)) && length(var.database_name) <= 63
    error_message = "Database name must start with letter, contain only lowercase/numbers/underscores, max 63 chars."
  }
}

variable "master_username" {
  description = "Master database username"
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9_]*$", var.master_username)) && length(var.master_username) <= 16
    error_message = "Username must start with letter, lowercase/numbers/underscores only, max 16 chars."
  }
}

variable "allocated_storage" {
  description = "Initial allocated storage in GB"
  type        = number

  validation {
    condition     = var.allocated_storage >= 20 && var.allocated_storage <= 65536
    error_message = "Allocated storage must be between 20 and 65536 GB."
  }
}

variable "max_allocated_storage" {
  description = "Maximum allocated storage for auto-scaling in GB"
  type        = number

  validation {
    condition     = var.max_allocated_storage >= var.allocated_storage
    error_message = "Max storage must be >= allocated storage."
  }
}

variable "subnet_group_name" {
  description = "Database subnet group name"
  type        = string
}

variable "security_group_ids" {
  description = "List of VPC security group IDs for RDS"
  type        = list(string)

  validation {
    condition     = length(var.security_group_ids) > 0
    error_message = "At least one security group must be specified."
  }
}

variable "backup_retention_days" {
  description = "Backup retention period (1-35 days)"
  type        = number

  validation {
    condition     = var.backup_retention_days >= 1 && var.backup_retention_days <= 35
    error_message = "Backup retention must be between 1 and 35 days."
  }
}

variable "multi_az" {
  description = "Enable Multi-AZ deployment (CRITICAL for production)"
  type        = bool
  default     = false
}

variable "storage_encrypted" {
  description = "Enable RDS storage encryption (always true for production)"
  type        = bool
  default     = true
}

variable "deletion_protection" {
  description = "Enable deletion protection (always true for production)"
  type        = bool
  default     = true
}

variable "skip_final_snapshot" {
  description = "Skip final snapshot on deletion (true for dev only)"
  type        = bool
  default     = false
}

variable "common_tags" {
  description = "Common tags to apply to RDS instance"
  type        = map(string)
  default     = {}
}

# =============================================================================
# DATA SOURCES
# =============================================================================

data "aws_region" "current" {}
