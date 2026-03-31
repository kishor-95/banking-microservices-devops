output "bastion_security_group_id" {
  description = "Bastion security group ID"
  value       = aws_security_group.bastion_host.id
}

output "eks_additional_security_group_id" {
  description = "EKS additional security group ID"
  value       = aws_security_group.eks_additional.id
}

output "rds_security_group_id" {
  description = "RDS security group ID"
  value       = aws_security_group.rds.id
}