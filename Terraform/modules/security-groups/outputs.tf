output "alb_security_group_id" {
  description = "ALB security group ID"
  value       = aws_security_group.alb.id
}

output "alb_security_group_name" {
  description = "ALB security group name"
  value       = aws_security_group.alb.name
}

output "eks_additional_security_group_id" {
  description = "Additional EKS security group ID"
  value       = aws_security_group.eks_additional.id
}

output "eks_additional_security_group_name" {
  description = "Additional EKS security group name"
  value       = aws_security_group.eks_additional.name
}

output "rds_security_group_id" {
  description = "RDS security group ID"
  value       = aws_security_group.rds.id
}

output "rds_security_group_name" {
  description = "RDS security group name"
  value       = aws_security_group.rds.name
}
