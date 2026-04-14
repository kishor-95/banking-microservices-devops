output "cluster_id" {
  description = "EKS cluster ID"
  value       = module.eks.cluster_id
}

output "cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "cluster_arn" {
  description = "EKS cluster ARN"
  value       = module.eks.cluster_arn
}

output "cluster_endpoint" {
  description = "EKS cluster API endpoint"
  value       = module.eks.cluster_endpoint
  sensitive   = true
}

output "cluster_version" {
  description = "EKS cluster Kubernetes version"
  value       = module.eks.cluster_version
}

output "cluster_certificate_authority_data" {
  description = "Base64 encoded certificate authority data for your cluster"
  value       = module.eks.cluster_certificate_authority_data
  sensitive   = true
}

output "cluster_security_group_id" {
  description = "Security group ID attached to EKS cluster"
  value       = module.eks.cluster_security_group_id
}

output "cluster_iam_role_arn" {
  description = "IAM role ARN for EKS cluster"
  value       = module.eks.cluster_iam_role_arn
}

output "cluster_iam_role_name" {
  description = "IAM role name for EKS cluster"
  value       = module.eks.cluster_iam_role_name
}

output "cluster_primary_security_group_id" {
  description = "EKS cluster primary security group ID"
  value       = module.eks.cluster_primary_security_group_id
}

output "node_security_group_id" {
  description = "Security group ID for EKS managed node group"
  value       = module.eks.node_security_group_id
}

output "eks_managed_node_groups" {
  description = "EKS managed node groups details"
  value       = module.eks.eks_managed_node_groups
}

# output "eks_managed_node_groups_id" {
#   description = "EKS managed node group IDs"
#   value       = { for k, v in module.eks.eks_managed_node_groups : k => v.v.node_group_name }
# }

output "oidc_provider_arn" {
  description = "ARN of the OIDC Provider for service account authentication"
  value       = module.eks.oidc_provider_arn
}

output "oidc_issuer_url" {
  description = "The URL on the EKS cluster OIDC Issuer"
  value       = module.eks.cluster_oidc_issuer_url
}

output "vpc_cni_irsa_iam_role_arn" {
  description = "IAM role ARN for VPC CNI IRSA"
  value       = module.vpc_cni_irsa.iam_role_arn
}

output "ebs_csi_irsa_iam_role_arn" {
  description = "IAM role ARN for EBS CSI IRSA"
  value       = module.ebs_csi_irsa.iam_role_arn
}

#output "aws_load_balancer_controller_irsa_iam_role_arn" {
#  description = "IAM role ARN for AWS Load Balancer Controller IRSA"
#  value       = module.aws_load_balancer_controller_irsa.iam_role_arn
#}

output "cluster_addons" {
  description = "Installed EKS cluster add-ons"
  value       = module.eks.cluster_addons
}

output "cloudwatch_log_group_name" {
  description = "CloudWatch log group name for EKS cluster logging"
  value       = module.eks.cloudwatch_log_group_name
}

output "cloudwatch_log_group_arn" {
  description = "CloudWatch log group ARN for EKS cluster logging"
  value       = module.eks.cloudwatch_log_group_arn
}
