# Local variables for cleaner code
locals {
  name_prefix = "${var.project_name}"
  
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }

  # Availability zones
  azs = slice(data.aws_availability_zones.available.names, 0, 2)

  # Subnet CIDR calculations
  public_subnet_cidrs     = [for k, v in local.azs : cidrsubnet(var.vpc_cidr, 4, k)]
  private_app_subnet_cidrs = [for k, v in local.azs : cidrsubnet(var.vpc_cidr, 4, k + 4)]
  private_db_subnet_cidrs  = [for k, v in local.azs : cidrsubnet(var.vpc_cidr, 4, k + 8)]
}

# Data source for availability zones
data "aws_availability_zones" "available" {
  state = "available"
}

# VPC Module
module "vpc" {
  source = "../../modules/vpc"

  vpc_name                 = "${local.name_prefix}-vpc"
  vpc_cidr                 = var.vpc_cidr
  availability_zones       = local.azs
  public_subnet_cidrs      = local.public_subnet_cidrs
  private_app_subnet_cidrs = local.private_app_subnet_cidrs
  private_db_subnet_cidrs  = local.private_db_subnet_cidrs
  cluster_name             = var.cluster_name
  environment              = var.environment
  single_nat_gateway       = var.single_nat_gateway
  one_nat_gateway_per_az   = var.one_nat_gateway_per_az
  common_tags              = local.common_tags
}

# EKS Module
module "eks" {
  source = "../../modules/eks"

  cluster_name             = var.cluster_name
  cluster_version          = var.cluster_version
  vpc_id                   = module.vpc.vpc_id
  private_subnet_ids       = module.vpc.private_app_subnet_ids
  node_instance_types      = var.node_instance_types
  node_min_size            = var.node_min_size
  node_max_size            = var.node_max_size
  node_desired_size        = var.node_desired_size
  environment              = var.environment
  common_tags              = local.common_tags

  depends_on = [module.vpc]
}

# Security Groups Module
module "security_groups" {
  source = "../../modules/security-groups"

  vpc_id                     = module.vpc.vpc_id
  name_prefix                = local.name_prefix
  allowed_ssh_cidr_blocks    = var.allowed_ssh_cidr_blocks
  eks_node_security_group_id = module.eks.node_security_group_id
  common_tags                = local.common_tags
  eks_cluster_security_group_id = module.eks.cluster_security_group_id

  depends_on = [module.eks]
}

# Bastion Module
module "bastion_host" {
  source = "../../modules/bastion_host"

  name_prefix         = local.name_prefix
  instance_type       = var.bastion_instance_type
  key_name            = var.ec2_key_name
  subnet_id           = module.vpc.public_subnet_ids[0]
  security_group_id   = module.security_groups.bastion_security_group_id
  create_eip          = true
  common_tags         = local.common_tags

  depends_on = [module.vpc, module.security_groups]
}

# RDS Module
module "rds" {
  source = "../../modules/rds"

  db_identifier           = "${local.name_prefix}-postgres"
  engine_version          = var.db_engine_version
  instance_class          = var.db_instance_class
  allocated_storage       = var.db_allocated_storage
  max_allocated_storage   = var.db_max_allocated_storage
  db_name                 = var.db_name
  db_username             = var.db_username
  db_subnet_group_name    = module.vpc.database_subnet_group_name
  security_group_ids      = [module.security_groups.rds_security_group_id]
  backup_retention_period = var.db_backup_retention_period
  deletion_protection     = var.db_deletion_protection
  skip_final_snapshot     = var.db_skip_final_snapshot
  common_tags             = local.common_tags

  depends_on = [module.vpc, module.security_groups]
}