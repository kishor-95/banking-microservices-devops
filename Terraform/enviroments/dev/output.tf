# VPC Outputs
output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
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

# EKS Outputs
output "eks_cluster_id" {
  description = "EKS cluster ID"
  value       = module.eks.cluster_id
}

output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
  sensitive   = true
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

output "aws_load_balancer_controller_role_arn" {
  description = "IAM role ARN for AWS Load Balancer Controller"
  value       = module.eks.aws_load_balancer_controller_role_arn
}

# Bastion Outputs
output "bastion_public_ip" {
  description = "Bastion host public IP"
  value       = module.bastion_host.public_ip
}

output "bastion_instance_id" {
  description = "Bastion instance ID"
  value       = module.bastion_host.instance_id
}

# RDS Outputs
output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = module.rds.db_instance_endpoint
  sensitive   = true
}

output "rds_database_name" {
  description = "RDS database name"
  value       = module.rds.db_instance_name
}

# Connection Information
output "connection_instructions" {
  description = "Instructions for connecting to the infrastructure"
  value = <<-EOT
    
    ====================================================================
    CONNECTION INSTRUCTIONS
    ====================================================================
    
    1. SSH to Bastion:
       ssh -i /path/to/${var.ec2_key_name}.pem ec2-user@${module.bastion_host.public_ip}
    
    2. Configure kubectl (from bastion):
       aws eks update-kubeconfig --region ${var.aws_region} --name ${var.cluster_name}
    
    3. Install AWS Load Balancer Controller:
       See: https://docs.aws.amazon.com/eks/latest/userguide/aws-load-balancer-controller.html
       Use IAM role ARN: ${module.eks.aws_load_balancer_controller_role_arn}
    
    4. RDS Connection:
       - Endpoint: ${module.rds.db_instance_endpoint}
       - Database: ${module.rds.db_instance_name}
       
    ====================================================================
  EOT
}