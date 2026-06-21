# =============================================================================
# LOCAL VARIABLES & DATA SOURCES
# =============================================================================

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
      Region      = var.aws_region
    },
    var.additional_tags
  )
}

# Get available AZs in the region
data "aws_availability_zones" "available" {
  state = "available"
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

# =============================================================================
# VPC MODULE - Foundation for everything else
# =============================================================================

module "vpc" {
  source = "../../modules/vpc"

  vpc_name                 = "${local.name_prefix}-vpc"
  vpc_cidr                 = var.vpc_cidr
  availability_zones       = slice(data.aws_availability_zones.available.names, 0, var.availability_zones_count)
  availability_zones_count = var.availability_zones_count
  cluster_name             = var.cluster_name
  environment              = var.environment
  single_nat_gateway       = var.single_nat_gateway
  enable_nat_gateway       = var.enable_nat_gateway
  common_tags              = local.common_tags
}

# =============================================================================
# EKS MODULE - MUST DEPLOY FIRST (before security groups can reference it)
# =============================================================================
# We deploy EKS before security groups because security groups need to reference
# the EKS node security group ID created by the EKS module

module "eks" {
  source = "../../modules/eks"

  cluster_name       = var.cluster_name
  cluster_version    = var.cluster_version
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_app_subnet_ids
  environment        = var.environment
  common_tags        = local.common_tags

  node_instance_types = var.node_instance_types
  node_min_size       = var.node_min_size
  node_max_size       = var.node_max_size
  node_desired_size   = var.node_desired_size

  depends_on = [module.vpc]
}

# =============================================================================
# SECURITY GROUPS MODULE - References EKS node security group
# =============================================================================

module "security_groups" {
  source = "../../modules/security-groups"

  name_prefix                = local.name_prefix
  vpc_id                     = module.vpc.vpc_id
  cluster_name               = var.cluster_name
  eks_node_security_group_id = module.eks.node_security_group_id
  enable_bastion             = false # Using SSM Session Manager instead
  common_tags                = local.common_tags

  depends_on = [module.vpc, module.eks]
}

# =============================================================================
# EKS MODULE - Kubernetes cluster with IRSA
# =============================================================================


# =============================================================================
# RDS MODULE - Managed PostgreSQL with encryption
# =============================================================================

module "rds" {
  source = "../../modules/rds"

  identifier            = "${local.name_prefix}-postgres"
  engine_version        = var.rds_engine_version
  instance_class        = var.rds_instance_class
  allocated_storage     = var.rds_allocated_storage
  max_allocated_storage = var.rds_max_allocated_storage
  database_name         = var.rds_database_name
  master_username       = var.rds_master_username

  subnet_group_name  = module.vpc.database_subnet_group_name
  security_group_ids = [module.security_groups.rds_security_group_id]

  backup_retention_days = var.rds_backup_retention_days
  multi_az              = var.rds_multi_az
  storage_encrypted     = var.rds_storage_encrypted
  deletion_protection   = var.rds_deletion_protection
  skip_final_snapshot   = var.rds_skip_final_snapshot

  common_tags = local.common_tags

  depends_on = [module.vpc, module.security_groups, module.eks]
}

# =============================================================================
# AWS LOAD BALANCER CONTROLLER - ALB/NLB support for ingress
# =============================================================================

module "aws_load_balancer_controller" {
  source = "../../modules/alb-controller"

  cluster_name              = var.cluster_name
  cluster_oidc_provider_arn = module.eks.oidc_provider_arn
  chart_version             = var.aws_load_balancer_controller_chart_version
  enable_deployment         = var.enable_aws_load_balancer_controller
  common_tags               = local.common_tags

  depends_on = [time_sleep.wait_for_eks_ready]
}
