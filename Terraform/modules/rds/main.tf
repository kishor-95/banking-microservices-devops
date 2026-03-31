# RDS PostgreSQL - Multi-AZ production database with encryption

module "rds" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.0"

  identifier = var.db_identifier

  # Engine configuration
  engine               = "postgres"
  engine_version       = var.engine_version
  family               = var.db_parameter_group_family
  major_engine_version = var.major_engine_version
  instance_class       = var.instance_class

  # Storage configuration
  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage
  storage_encrypted     = true
  storage_type          = "gp3"
  iops                  = 3000

  # Database configuration
  db_name  = var.db_name
  username = var.db_username
  # password = var.db_password
  port     = 5432

  # Password management - use random password, stored in Secrets Manager
  manage_master_user_password = true

  # High availability
  multi_az               = true
  db_subnet_group_name   = var.db_subnet_group_name
  vpc_security_group_ids = var.security_group_ids

  # Public access disabled - private only
  publicly_accessible = false

  # Backup configuration
  backup_retention_period = var.backup_retention_period
  backup_window           = "03:00-04:00"  # 3-4 AM IST
  maintenance_window      = "Mon:04:00-Mon:05:00"  # Monday 4-5 AM IST

  # Deletion protection for production
  deletion_protection = var.deletion_protection
  skip_final_snapshot = var.skip_final_snapshot
  # final_snapshot_identifier = var.skip_final_snapshot ? null : "${var.db_identifier}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"

  # Enhanced monitoring
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  create_cloudwatch_log_group     = true
  monitoring_interval             = 60
  monitoring_role_name            = "${var.db_identifier}-monitoring-role"
  create_monitoring_role          = true

  # Performance Insights
  performance_insights_enabled    = true
  performance_insights_retention_period = 7

  # Parameter group
  parameters = [
    {
      name  = "log_connections"
      value = "1"
    },
    {
      name  = "log_disconnections"
      value = "1"
    },
    {
      name  = "log_duration"
      value = "1"
    },
    {
      name  = "log_lock_waits"
      value = "1"
    },
    {
      name  = "log_statement"
      value = "all"
    },
    {
      name  = "shared_preload_libraries"
      value = "pg_stat_statements"
    }
  ]

  tags = merge(
    var.common_tags,
    {
      Name = var.db_identifier
    }
  )
}