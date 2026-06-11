# =============================================================================
# VPC MODULE - Battle-tested terraform-aws-modules/vpc
# =============================================================================
# This module creates:
# - VPC with configurable CIDR
# - Public subnets in multiple AZs with NAT gateways
# - Private app subnets for EKS nodes
# - Private database subnets for RDS
# - Database subnet group
# - Internet gateway
# - Route tables with proper isolation
# =============================================================================

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      #     version = ">= 6.42.0"
    }
  }
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.4"

  name = var.vpc_name
  cidr = var.vpc_cidr

  azs              = var.availability_zones
  public_subnets  = [for k, az in var.availability_zones : cidrsubnet(var.vpc_cidr, 4, k)]
  private_subnets = [for k, az in var.availability_zones : cidrsubnet(var.vpc_cidr, 4, k + var.availability_zones_count)]
  database_subnets = [for k, az in var.availability_zones : cidrsubnet(var.vpc_cidr, 4, k + (var.availability_zones_count * 2))]

  # DNS configuration for EKS cluster discovery and service discovery
  enable_dns_hostnames = true
  enable_dns_support   = true

  # NAT Gateway configuration
  enable_nat_gateway = var.enable_nat_gateway
  single_nat_gateway = var.single_nat_gateway
  one_nat_gateway_per_az = !var.single_nat_gateway

  # Database subnet group for RDS
  create_database_subnet_group           = true
  database_subnet_group_name             = "${var.vpc_name}-db-subnet-group"
  create_database_subnet_route_table     = true
  create_database_nat_gateway_route      = true

  # Public subnet tags for AWS Load Balancer Controller (ALB discovery)
  public_subnet_tags = {
    "kubernetes.io/role/elb"                    = "1"
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
    "Type"                                       = "Public"
  }

  # Private subnet tags for EKS nodes and Load Balancer Controller (internal)
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb"           = "1"
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
    "Type"                                       = "Private-App"
  }

  # Database subnet tags
  database_subnet_tags = {
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
    "Type"                                       = "Private-Database"
  }

  tags = merge(
    var.common_tags,
    {
      Name              = var.vpc_name
      Environment       = var.environment
      ClusterName       = var.cluster_name
      Terraform         = "true"
    }
  )
}

data "aws_region" "current" {}
