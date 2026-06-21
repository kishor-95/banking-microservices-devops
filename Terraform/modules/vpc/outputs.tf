output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "vpc_cidr_block" {
  description = "VPC CIDR block"
  value       = module.vpc.vpc_cidr_block
}

output "vpc_arn" {
  description = "VPC ARN"
  value       = module.vpc.vpc_arn
}

output "public_subnet_ids" {
  description = "Public subnet IDs (ALB tier)"
  value       = module.vpc.public_subnets
}

output "private_app_subnet_ids" {
  description = "Private app subnet IDs (EKS node tier)"
  value       = module.vpc.private_subnets
}

output "private_db_subnet_ids" {
  description = "Private database subnet IDs (RDS tier)"
  value       = module.vpc.database_subnets
}

output "database_subnet_group_name" {
  description = "RDS subnet group name"
  value       = module.vpc.database_subnet_group_name
}

output "nat_gateway_ids" {
  description = "NAT Gateway IDs"
  value       = module.vpc.natgw_ids
}

output "nat_gateway_public_ips" {
  description = "NAT Gateway public IPs"
  value       = module.vpc.nat_public_ips
}

output "internet_gateway_id" {
  description = "Internet Gateway ID"
  value       = module.vpc.igw_id
}

output "public_route_table_ids" {
  description = "Public route table IDs"
  value       = module.vpc.public_route_table_ids
}

output "private_route_table_ids" {
  description = "Private route table IDs"
  value       = module.vpc.private_route_table_ids
}

output "database_route_table_ids" {
  description = "Database route table IDs"
  value       = module.vpc.database_route_table_ids
}
