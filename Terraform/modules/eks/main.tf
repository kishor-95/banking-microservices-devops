# EKS Cluster - Production-grade Kubernetes with private API endpoint
# Using official terraform-aws-modules/eks

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version

  # Private cluster - API endpoint not publicly accessible
  cluster_endpoint_public_access  = false
  cluster_endpoint_private_access = true

  # Enable Cluster logging
    # Enable CloudWatch Control Plane Logging
  cluster_enabled_log_types = [
  "api",
  "audit",
  "authenticator",
  "controllerManager",
  "scheduler"
 ]

  # Optional: log retention (recommended)
  cloudwatch_log_group_retention_in_days = 7

   # Cluster access through bastion only
  cluster_additional_security_group_ids = var.additional_security_group_ids

  vpc_id     = var.vpc_id
  subnet_ids = var.private_subnet_ids

  # Enable IRSA (IAM Roles for Service Accounts)
  enable_irsa = true

  # Cluster encryption using default AWS managed KMS
  cluster_encryption_config = {
    resources        = ["secrets"]
    provider_key_arn = null  # Uses AWS managed key
  }

  # EKS Managed Node Group
  eks_managed_node_groups = {
    main = {
      name = "${var.cluster_name}-node-group"

      instance_types = var.node_instance_types
      capacity_type  = "ON_DEMAND"  # For banking, avoid SPOT instances
      vpc_security_group_ids = [module.security-groups.aws_security_group.eks_additional.id]

      min_size     = var.node_min_size
      max_size     = var.node_max_size
      desired_size = var.node_desired_size

      # Launch template for custom configuration
      create_launch_template = true
      launch_template_name   = "${var.cluster_name}-node-lt"

      block_device_mappings = {
        xvda = {
          device_name = "/dev/xvda"
          ebs = {
            volume_size           = 20
            volume_type           = "gp3"
            iops                  = 3000
            throughput            = 150
            encrypted             = true
            delete_on_termination = true
          }
        }
      }

      # IMDSv2 required
      metadata_options = {
        http_endpoint               = "enabled"
        http_tokens                 = "required"
        http_put_response_hop_limit = 2
      }

      # Taints and labels for workload segregation
      labels = {
        Environment = var.environment
        Workload    = "general"
      }

      tags = merge(
        var.common_tags,
        {
          Name = "${var.cluster_name}-node-group"
        }
      )
    }
  }


  # Cluster access management
  enable_cluster_creator_admin_permissions = true

  # EKS Add-ons
  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent              = true
      service_account_role_arn = module.vpc_cni_irsa.iam_role_arn
    }
    aws-ebs-csi-driver = {
      most_recent              = true
      service_account_role_arn = module.ebs_csi_irsa.iam_role_arn
    }
  }

  tags = merge(
    var.common_tags,
    {
      Name = var.cluster_name
    }
  )
}

# IRSA for VPC CNI
module "vpc_cni_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.0"

  role_name = "${var.cluster_name}-vpc-cni-irsa"

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

# IRSA for EBS CSI Driver
module "ebs_csi_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.0"

  role_name = "${var.cluster_name}-ebs-csi-irsa"

  attach_ebs_csi_policy = true

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:ebs-csi-controller-sa"]
    }
  }

  tags = var.common_tags
}