
# # ─── VPC ──────────────────────────────────────────────────────────────────────
# module "vpc" {
#   source = "../modules/vpc"

#   project_name         = var.project_name
#   environment          = var.environment
#   vpc_cidr             = var.vpc_cidr
#   availability_zones   = var.availability_zones
#   public_subnet_cidrs  = var.public_subnet_cidrs
#   private_eks_cidrs    = var.private_eks_cidrs
#   private_db_cidrs     = var.private_db_cidrs
# }

# # ─── SECURITY GROUPS ─────────────────────────────────────────────────────────
# module "security_groups" {
#   source = "./modules/security_groups"

#   project_name    = var.project_name
#   environment     = var.environment
#   vpc_id          = module.vpc.vpc_id
#   vpc_cidr        = var.vpc_cidr
#   nodeport_range  = var.nodeport_range
# }

# # ─── IAM ─────────────────────────────────────────────────────────────────────
# module "iam" {
#   source = "./modules/iam"

#   project_name        = var.project_name
#   environment         = var.environment
#   eks_cluster_name    = local.eks_cluster_name
#   aws_region          = var.aws_region
#   aws_account_id      = data.aws_caller_identity.current.account_id
#   oidc_provider_url   = module.eks.oidc_provider_url   # populated after EKS is created
#   oidc_provider_arn   = module.eks.oidc_provider_arn
# }

# # ─── EKS ─────────────────────────────────────────────────────────────────────
# module "eks" {
#   source = "./modules/eks"

#   project_name          = var.project_name
#   environment           = var.environment
#   cluster_name          = local.eks_cluster_name
#   cluster_version       = var.eks_cluster_version
#   vpc_id                = module.vpc.vpc_id
#   private_subnet_ids    = module.vpc.private_eks_subnet_ids
#   eks_cluster_role_arn  = module.iam.eks_cluster_role_arn
#   eks_node_role_arn     = module.iam.eks_node_role_arn
#   eks_sg_id             = module.security_groups.eks_sg_id
#   node_instance_types   = var.node_instance_types
#   node_desired_size     = var.node_desired_size
#   node_min_size         = var.node_min_size
#   node_max_size         = var.node_max_size
#   node_disk_size        = var.node_disk_size
# }

# # ─── RDS ─────────────────────────────────────────────────────────────────────
# module "rds" {
#   source = "./modules/rds"

#   project_name        = var.project_name
#   environment         = var.environment
#   vpc_id              = module.vpc.vpc_id
#   db_subnet_ids       = module.vpc.private_db_subnet_ids
#   db_sg_id            = module.security_groups.db_sg_id
#   db_name             = var.db_name
#   db_username         = var.db_username
#   db_password         = var.db_password
#   db_instance_class   = var.db_instance_class
#   db_engine_version   = var.db_engine_version
#   db_allocated_storage = var.db_allocated_storage
#   multi_az            = var.rds_multi_az
# }

# # ─── BASTION ─────────────────────────────────────────────────────────────────
# module "bastion" {
#   source = "./modules/bastion"

#   project_name       = var.project_name
#   environment        = var.environment
#   vpc_id             = module.vpc.vpc_id
#   public_subnet_id   = module.vpc.public_subnet_ids[0]
#   bastion_sg_id      = module.security_groups.bastion_sg_id
#   bastion_role_arn   = module.iam.bastion_instance_profile_arn
#   key_pair_name      = var.key_pair_name
#   instance_type      = var.bastion_instance_type
#   eks_cluster_name   = local.eks_cluster_name
#   aws_region         = var.aws_region
# }

# # ─── ECR ─────────────────────────────────────────────────────────────────────
# # module "ecr" {
# #   source = "./modules/ecr"

# #   project_name   = var.project_name
# #   environment    = var.environment
# #   repositories   = var.ecr_repositories
# #   aws_account_id = data.aws_caller_identity.current.account_id
# # }

# # ─── NLB (aws-load-balancer-controller annotations drive this) ───────────────
# module "nlb" {
#   source = "./modules/nlb"

#   project_name               = var.project_name
#   environment                = var.environment
#   vpc_id                     = module.vpc.vpc_id
#   public_subnet_ids          = module.vpc.public_subnet_ids
#   nlb_sg_id                  = module.security_groups.nlb_sg_id
#   eks_cluster_name           = local.eks_cluster_name
#   lb_controller_role_arn     = module.iam.lb_controller_role_arn
#   eks_oidc_provider_arn      = module.eks.oidc_provider_arn
# }

# # ─── DATA SOURCES ─────────────────────────────────────────────────────────────
# data "aws_caller_identity" "current" {}

# # ─── LOCALS ──────────────────────────────────────────────────────────────────
# locals {
#   eks_cluster_name = "${var.project_name}-${var.environment}-eks"
# }


# Local variables for cleaner code
locals {
  name_prefix = "${var.project_name}-${var.environment}"
  
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

  depends_on = [module.eks]
}

# Bastion Module
module "bastion" {
  source = "../../modules/bastion"

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