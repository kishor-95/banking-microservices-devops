# =============================================================================
# RDS MODULE - Production PostgreSQL Database
# =============================================================================
# Features:
# - AWS managed RDS PostgreSQL
# - Automatic backups with configurable retention
# - Multi-AZ deployment (optional but recommended for production)
# - Storage encryption with AWS managed KMS key
# - No hardcoded passwords (auto-generated, stored in Secrets Manager)
# - Enhanced monitoring and CloudWatch logging
# - Performance Insights enabled
# - Automatic storage scaling
# - Deletion protection enabled by default
# =============================================================================

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.45"
    }
  }
}

module "rds" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.1"

  identifier = var.identifier

  # ==========================================================================
  # ENGINE CONFIGURATION
  # ==========================================================================
  engine               = "postgres"
  engine_version       = var.engine_version
  family               = "postgres${split(".", var.engine_version)[0]}"
  major_engine_version = split(".", var.engine_version)[0]
  instance_class       = var.instance_class

  # ==========================================================================
  # DATABASE CONFIGURATION
  # ==========================================================================
  db_name  = var.database_name
  username = var.master_username
  password = null  # Let AWS generate and manage password

  # Automatic password management via AWS Secrets Manager
  manage_master_user_password = true
  master_user_secret_kms_key_id = null  # Uses default AWS managed key

  port = 5432

  # ==========================================================================
  # STORAGE CONFIGURATION
  # ==========================================================================
  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage  # Auto-scaling enabled
  storage_type          = "gp3"  # Latest generation, better performance
  storage_encrypted     = var.storage_encrypted
  iops                  = null   # 3000 IOPS baseline for gp3
  storage_throughput    = null   # 125 MB/s baseline for gp3

  # ==========================================================================
  # BACKUP & RECOVERY
  # ==========================================================================
  backup_retention_period = var.backup_retention_days
  backup_window           = "03:00-04:00"  # UTC - adjust for your timezone
  copy_tags_to_snapshot   = true
  skip_final_snapshot     = var.skip_final_snapshot

  # ==========================================================================
  # HIGH AVAILABILITY
  # ==========================================================================
  multi_az = var.multi_az

  # ==========================================================================
  # NETWORKING & SECURITY
  # ==========================================================================
  db_subnet_group_name            = var.subnet_group_name
  publicly_accessible             = false  # Never public for banking
  vpc_security_group_ids          = var.security_group_ids
  # associate_security_group_by_name = false

  # ==========================================================================
  # MAINTENANCE & UPDATES
  # ==========================================================================
  maintenance_window              = "Mon:04:00-Mon:05:00"  # UTC - adjust for your timezone
  auto_minor_version_upgrade      = true
  deletion_protection             = var.deletion_protection
  enabled_cloudwatch_logs_exports = ["postgresql"]

  # ==========================================================================
  # PERFORMANCE & MONITORING
  # ==========================================================================
  performance_insights_enabled          = true
  performance_insights_retention_period = 7
  create_monitoring_role                = true
  monitoring_interval                   = 60
  monitoring_role_name                  = "${var.identifier}-monitoring-role"

  # CloudWatch logging for PostgreSQL
  # cloudwatch_log_group_name            = "/aws/rds/instance/${var.identifier}/postgresql"
  #enabled_cloudwatch_logs_exports = ["postgresql"]
  cloudwatch_log_group_retention_in_days = 30

  # ==========================================================================
  # DATABASE PARAMETERS (Security & Logging)
  # ==========================================================================
  # These parameters are for logging and security best practices
  parameters = [
    {
      name         = "log_connections"
      value        = "1"
      apply_method = "immediate"
    },
    {
      name         = "log_disconnections"
      value        = "1"
      apply_method = "immediate"
    },
    {
      name         = "log_duration"
      value        = "1"  # Log duration of all statements
      apply_method = "immediate"
    },
    {
      name         = "log_lock_waits"
      value        = "1"
      apply_method = "immediate"
    },
    {
      name         = "log_statement"
      value        = "all"  # Log all statements (can be heavy - adjust to 'ddl' for production)
      apply_method = "pending-reboot"
    },
    {
      name         = "log_min_duration_statement"
      value        = "5000"  # Log slow queries (> 5 seconds)
      apply_method = "immediate"
    },
    {
      name         = "shared_preload_libraries"
      value        = "pg_stat_statements"  # Enable query statistics
      apply_method = "pending-reboot"
    },
    {
      name         = "password_encryption"
      value        = "scram-sha-256"  # Secure password encryption
      apply_method = "immediate"
    }
  ]

  # ==========================================================================
  # TAGS
  # ==========================================================================
  tags = merge(
    var.common_tags,
    {
      Name = var.identifier
    }
  )
}

# =============================================================================
# OPTIONAL: RDS ENHANCED MONITORING ROLE POLICY
# =============================================================================
# The module creates the role, but ensure it has proper permissions
# This is handled by the module's create_monitoring_role flag

# =============================================================================
# OPTIONAL: RDS CLUSTER PARAMETER GROUP (if using Aurora)
# =============================================================================
# This module uses RDS for single instance PostgreSQL, not Aurora.
# If you switch to Aurora, you'll need cluster parameter groups.
