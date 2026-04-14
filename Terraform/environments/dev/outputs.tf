# =============================================================================
# VPC OUTPUTS
# =============================================================================

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "vpc_cidr" {
  description = "VPC CIDR block"
  value       = module.vpc.vpc_cidr_block
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnet_ids
}

output "private_app_subnet_ids" {
  description = "Private app subnet IDs"
  value       = module.vpc.private_app_subnet_ids
}

output "private_db_subnet_ids" {
  description = "Private database subnet IDs"
  value       = module.vpc.private_db_subnet_ids
}

output "nat_gateway_ids" {
  description = "NAT Gateway IDs"
  value       = module.vpc.nat_gateway_ids
}

# =============================================================================
# EKS CLUSTER OUTPUTS
# =============================================================================

output "eks_cluster_id" {
  description = "EKS cluster ID"
  value       = module.eks.cluster_id
}

output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "eks_cluster_arn" {
  description = "EKS cluster ARN"
  value       = module.eks.cluster_arn
}

output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
  sensitive   = true
}

output "eks_cluster_version" {
  description = "EKS cluster Kubernetes version"
  value       = module.eks.cluster_version
}

output "eks_cluster_security_group_id" {
  description = "EKS cluster security group ID"
  value       = module.eks.cluster_security_group_id
}

output "eks_node_security_group_id" {
  description = "EKS node security group ID"
  value       = module.eks.node_security_group_id
}

output "eks_oidc_provider_arn" {
  description = "EKS OIDC provider ARN for IRSA"
  value       = module.eks.oidc_provider_arn
}

output "eks_oidc_issuer_url" {
  description = "EKS OIDC issuer URL"
  value       = module.eks.oidc_issuer_url
}

# =============================================================================
# RDS DATABASE OUTPUTS
# =============================================================================

output "rds_endpoint" {
  description = "RDS instance endpoint (host:port)"
  value       = module.rds.db_instance_endpoint
  sensitive   = true
}

output "rds_address" {
  description = "RDS instance address only"
  value       = module.rds.db_instance_address
  sensitive   = true
}

output "rds_port" {
  description = "RDS instance port"
  value       = module.rds.db_instance_port
}

output "rds_database_name" {
  description = "RDS database name"
  value       = module.rds.db_instance_name
}

output "rds_master_username" {
  description = "RDS master username"
  value       = module.rds.db_instance_username
  sensitive   = true
}

output "rds_arn" {
  description = "RDS instance ARN"
  value       = module.rds.db_instance_arn
}

#output "rds_storage_type" {
#  description = "RDS storage type"
#  value       = module.rds.db_instance_storage_type
#}

#output "rds_allocated_storage" {
#  description = "RDS allocated storage in GB"
#  value       = module.rds.db_instance_allocated_storage
#}

#output "rds_multi_az" {
#  description = "RDS Multi-AZ enabled"
#  value       = module.rds.db_instance_multi_az
#}

# =============================================================================
# AWS LOAD BALANCER CONTROLLER OUTPUTS
# =============================================================================

output "aws_load_balancer_controller_iam_role_arn" {
  description = "IAM role ARN for AWS Load Balancer Controller"
  value       = module.aws_load_balancer_controller.iam_role_arn
}

output "aws_load_balancer_controller_helm_release" {
  description = "Helm release status of AWS Load Balancer Controller"
  value       = module.aws_load_balancer_controller.helm_release_status
}

# =============================================================================
# KUBECONFIG COMMAND
# =============================================================================

output "configure_kubectl" {
  description = "Command to configure kubectl for the EKS cluster"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name}"
}

output "cluster_access_entry_command" {
  description = "Command to grant additional IAM principal access to the cluster"
  value       = "aws eks create-access-entry --cluster-name ${module.eks.cluster_name} --principal-arn <IAM_PRINCIPAL_ARN> --region ${var.aws_region}"
}

# =============================================================================
# CONNECTION STRING (dev only - remove for production)
# =============================================================================

output "rds_connection_string" {
  description = "PostgreSQL connection string (dev only)"
  value       = "postgresql://${module.rds.db_instance_username}:PASSWORD@${module.rds.db_instance_address}:${module.rds.db_instance_port}/${module.rds.db_instance_name}"
  sensitive   = true
}

# =============================================================================
# DEBUG & OPERATIONAL COMMANDS
# =============================================================================

output "kubectl_get_nodes" {
  description = "Command to check EKS nodes"
  value       = "kubectl get nodes"
}

output "kubectl_check_alb_controller" {
  description = "Command to verify AWS Load Balancer Controller deployment"
  value       = "kubectl get deployment -n kube-system aws-load-balancer-controller"
}

output "kubectl_check_irsa" {
  description = "Command to verify IRSA setup"
  value       = "kubectl get serviceaccount -n kube-system -o jsonpath='{.items[*].metadata.annotations}' | grep 'eks.amazonaws.com/role-arn'"
}
