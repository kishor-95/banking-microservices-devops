# VPC Module - Production-grade networking foundation
# Using official terraform-aws-modules/vpc for battle-tested reliability

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 6.0"

  name = var.vpc_name
  cidr = var.vpc_cidr

  azs              = var.availability_zones
  public_subnets   = var.public_subnet_cidrs
  private_subnets  = var.private_app_subnet_cidrs
  database_subnets = var.private_db_subnet_cidrs

  # Enable DNS for EKS cluster discovery
  enable_dns_hostnames = true
  enable_dns_support   = true

  # Single NAT Gateway for cost optimization
  # WARNING: This creates a SPOF. For production banking, use one_nat_gateway_per_az = true
  enable_nat_gateway = true
  single_nat_gateway = var.single_nat_gateway
  one_nat_gateway_per_az = var.one_nat_gateway_per_az

  # Create database subnet group for RDS
  create_database_subnet_group = true

  # Kubernetes subnet tagging for AWS Load Balancer Controller auto-discovery
  public_subnet_tags = {
    "kubernetes.io/role/elb"                    = "1"
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb"           = "1"
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
  }

  database_subnet_tags = {
    Name = "${var.vpc_name}-db-subnet"
  }

  tags = merge(
    var.common_tags,
    {
      Name        = var.vpc_name
      Environment = var.environment
      Terraform   = "true"
    }
  )
}