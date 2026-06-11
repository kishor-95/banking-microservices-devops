# =============================================================================
# AWS CONFIGURATION
# =============================================================================
aws_region   = "ap-south-1"
environment  = "dev"
project_name = "bankapp"

# =============================================================================
# VPC CONFIGURATION
# =============================================================================
vpc_cidr                 = "10.0.0.0/16"
availability_zones_count = 2
single_nat_gateway       = true # Cost optimization for dev
enable_nat_gateway       = true

# =============================================================================
# EKS CLUSTER CONFIGURATION
# =============================================================================
cluster_name               = "bankapp-eks"
cluster_version            = "1.34"
node_instance_types        = ["c7i-flex.large"] # Changed from c7i-flex.large for cost savings
node_min_size              = 2
node_max_size              = 5
node_desired_size          = 2
enable_cluster_autoscaling = true

# =============================================================================
# RDS DATABASE CONFIGURATION
# =============================================================================
rds_engine_version        = "17.6"
rds_instance_class        = "db.t3.micro" # Changed from micro - not suitable for banking
rds_allocated_storage     = 20
rds_max_allocated_storage = 100
rds_database_name         = "bankapp"
rds_master_username       = "dbadmin"
rds_backup_retention_days = 1     # Reduced for dev, increase for prod
rds_multi_az              = false # Acceptable for dev only
rds_storage_encrypted     = false
rds_deletion_protection   = false
rds_skip_final_snapshot   = true # OK for dev, set to false for prod

# =============================================================================
# AWS LOAD BALANCER CONTROLLER
# =============================================================================
aws_load_balancer_controller_chart_version = "3.2.1"
enable_aws_load_balancer_controller        = true

# =============================================================================
# ADDITIONAL TAGS
# =============================================================================
additional_tags = {
  Terraform  = "true"
  Owner      = "Kishor"
#  CostCenter = "Engineering"
}
