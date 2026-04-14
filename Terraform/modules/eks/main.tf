# =============================================================================
# EKS CLUSTER MODULE - Production-grade Kubernetes on AWS
# =============================================================================
# Features:
# - EKS managed Kubernetes cluster
# - Managed node groups with auto-scaling
# - OIDC provider for IRSA (IAM Roles for Service Accounts)
# - VPC CNI and EBS CSI driver add-ons
# - Control plane logging
# - KMS encryption for secrets
# - IMDSv2 requirement for security
# =============================================================================

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.45"
    }
  }
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.4"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version

  # ==========================================================================
  # CLUSTER ENDPOINT CONFIGURATION
  # ==========================================================================
  # Both public and private endpoints enabled for flexibility
  cluster_endpoint_public_access  = true
  cluster_endpoint_private_access = true
  cluster_endpoint_public_access_cidrs = ["0.0.0.0/0"]

  # ==========================================================================
  # NETWORKING
  # ==========================================================================
  vpc_id     = var.vpc_id
  subnet_ids = var.private_subnet_ids

  # ==========================================================================
  # CLUSTER LOGGING & MONITORING
  # ==========================================================================
  # Enable all control plane logging to CloudWatch
  cluster_enabled_log_types = [
    "api",
    "audit",
    "authenticator",
    "controllerManager",
    "scheduler"
  ]
  cloudwatch_log_group_retention_in_days = 30

  # ==========================================================================
  # SECURITY & ENCRYPTION
  # ==========================================================================
  # Enable IRSA (IAM Roles for Service Accounts) for fine-grained IAM
  enable_irsa = true

  # Encrypt secrets at rest using AWS managed KMS key
  cluster_encryption_config = {
    provider_key_arn = null  # Uses AWS managed key (aws/eks)
    resources        = ["secrets"]
  }

  # ==========================================================================
  # MANAGED NODE GROUPS
  # ==========================================================================
  eks_managed_node_groups = {
    main = {
      name            = "${var.cluster_name}-managed-ng"
      use_name_prefix = true

      # Instance configuration
      instance_types = var.node_instance_types
      capacity_type  = "ON_DEMAND"  # No SPOT for banking workloads

      # Scaling configuration
      min_size     = var.node_min_size
      max_size     = var.node_max_size
      desired_size = var.node_desired_size

      # Update strategy (rolling deployment)
      update_config = {
        max_unavailable_percentage = 33
      }

      # Launch template configuration
      create_launch_template = true
      launch_template_name   = "${var.cluster_name}-launch-template"
      launch_template_version = "$Latest"

      # EBS configuration with encryption
      block_device_mappings = {
        xvda = {
          device_name = "/dev/xvda"
          ebs = {
            volume_size           = 20         # Sufficient for container runtime + logs
            volume_type           = "gp3"
            iops                  = 3000
            throughput            = 125
            delete_on_termination = true
            encrypted             = true
          }
        }
      }

      # IMDSv2 enforcement - critical security control
      metadata_options = {
        http_endpoint               = "enabled"
        http_tokens                 = "required"      # IMDSv2 required
        http_put_response_hop_limit = 2
      }

      # Tags and labels
      labels = {
        Environment = var.environment
        ManagedBy   = "Terraform"
        NodeGroup   = "main"
      }

      tags = merge(
        var.common_tags,
        {
          Name = "${var.cluster_name}-managed-ng"
        }
      )
    }
  }

  # ==========================================================================
  # EKS ADD-ONS - Core CNI, monitoring, storage
  # ==========================================================================
  cluster_addons = {
    # CoreDNS - Kubernetes DNS
    coredns = {
      most_recent = true
      timeouts = {
        create = "10m"
        delete = "10m"
      }
    }

    # Kube Proxy - Kubernetes networking
    kube-proxy = {
      most_recent = true
      timeouts = {
        create = "10m"
        delete = "10m"
      }
    }

    # VPC CNI - AWS-native networking for pods
    vpc-cni = {
      most_recent = true
      service_account_role_arn = module.vpc_cni_irsa.iam_role_arn
      timeouts = {
        create = "10m"
        delete = "10m"
      }
    }

    # EBS CSI Driver - Block storage for persistent volumes
    aws-ebs-csi-driver = {
      most_recent = true
      service_account_role_arn = module.ebs_csi_irsa.iam_role_arn
      timeouts = {
        create = "10m"
        delete = "10m"
      }
    }
  }

  # ==========================================================================
  # ACCESS & PERMISSIONS
  # ==========================================================================
  # Grant cluster creator admin access
  enable_cluster_creator_admin_permissions = true

  # ==========================================================================
  # TAGS
  # ==========================================================================
  tags = merge(
    var.common_tags,
    {
      Name = var.cluster_name
    }
  )
}

# =============================================================================
# IRSA FOR VPC CNI
# =============================================================================
module "vpc_cni_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.34"

  role_name_prefix = "${var.cluster_name}-vpc-cni-"

  attach_vpc_cni_policy = true
  vpc_cni_enable_ipv4   = true

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:aws-node"]
    }
  }

  tags = var.common_tags
}

# =============================================================================
# IRSA FOR EBS CSI DRIVER
# =============================================================================
module "ebs_csi_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.34"

  role_name_prefix = "${var.cluster_name}-ebs-csi-"

  attach_ebs_csi_policy = true

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:ebs-csi-controller-sa"]
    }
  }

  tags = var.common_tags
}

# # =============================================================================
# # IRSA FOR AWS LOAD BALANCER CONTROLLER
# # =============================================================================
# module "aws_load_balancer_controller_irsa" {
#   source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
#   version = "~> 5.34"

#   role_name_prefix = "${var.cluster_name}-aws-lb-ctrl"

#   attach_load_balancer_controller_policy = true

#   oidc_providers = {
#     main = {
#       provider_arn               = module.eks.oidc_provider_arn
#       namespace_service_accounts = ["kube-system:aws-load-balancer-controller"]
#     }
#   }

#   tags = var.common_tags
# }
