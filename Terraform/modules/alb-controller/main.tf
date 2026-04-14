# =============================================================================
# AWS LOAD BALANCER CONTROLLER MODULE
# =============================================================================
# Deploys the AWS Load Balancer Controller using Helm
# This enables ALB/NLB ingress controllers in EKS
#
# Requirements:
# - EKS cluster with IRSA enabled
# - OIDC provider configured
# - VPC CNI installed
# =============================================================================

terraform {
  required_providers {
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.13"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.45"
    }
  }
}

# =============================================================================
# IAM ROLE FOR AWS LOAD BALANCER CONTROLLER (IRSA)
# =============================================================================
module "aws_load_balancer_controller_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.34"

  role_name_prefix = "${var.cluster_name}-aws-lb-ctrl"

  attach_load_balancer_controller_policy = true

  oidc_providers = {
    main = {
      provider_arn               = var.cluster_oidc_provider_arn
      namespace_service_accounts = ["kube-system:aws-load-balancer-controller"]
    }
  }

  tags = var.common_tags
}

# =============================================================================
# HELM RELEASE - AWS LOAD BALANCER CONTROLLER
# =============================================================================
resource "helm_release" "aws_load_balancer_controller" {
  count = var.enable_deployment ? 1 : 0

  name       = "aws-load-balancer-controller"
  repository = "https://aws.github.io/eks-charts"
  chart      = "aws-load-balancer-controller"
  namespace  = "kube-system"
  version    = var.chart_version

  # Wait for previous installs to complete
  depends_on = [module.aws_load_balancer_controller_irsa, kubernetes_namespace_v1.ingress_ns]

  # Values for the Helm chart
  values = [
    yamlencode({
      clusterName = var.cluster_name

      enableShield       = false
      enableWaf          = false
      enableWafv2        = false
      logLevel           = "info"
      webhookBindPort    = 9443

      # IRSA service account configuration
      serviceAccount = {
        create = true
        name   = "aws-load-balancer-controller"
        annotations = {
          "eks.amazonaws.com/role-arn" = module.aws_load_balancer_controller_irsa.iam_role_arn
        }
      }

      # Controller replicas for HA
      replicaCount = 2

      # Resource requests/limits
      resources = {
        limits = {
          cpu    = "200m"
          memory = "500Mi"
        }
        requests = {
          cpu    = "100m"
          memory = "200Mi"
        }
      }

      # Security context
      securityContext = {
        allowPrivilegeEscalation = false
        readOnlyRootFilesystem   = true
        runAsNonRoot             = true
        capabilities = {
          drop = ["ALL"]
        }
      }

      # Node selector (optional - run on specific nodes)
      # nodeSelector = {
      #   workload = "monitoring"
      # }

      # Tolerations (if using node taints)
      # tolerations = []

      # Pod disruption budget for HA
      podDisruptionBudget = {
        maxUnavailable = 1
      }
    })
  ]

  timeout = 300

  # Cleanup on deletion
  cleanup_on_fail = true
}

# =============================================================================
# NAMESPACE LABEL FOR ALB DISCOVERY (optional but recommended)
# =============================================================================
# ALB Controller uses these labels to discover ingresses
resource "kubernetes_namespace_v1" "ingress_ns" {
  count = var.enable_deployment ? 1 : 0

  metadata {
    name = "ingress-alb"
    labels = {
      "app.kubernetes.io/name" = "aws-load-balancer-controller"
    }
  }
}
