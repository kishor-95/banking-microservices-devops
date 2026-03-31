output "db_instance_endpoint" {
  description = "RDS instance endpoint"
  value       = module.rds.db_instance_endpoint
  sensitive   = true
}

output "db_instance_address" {
  description = "RDS instance address"
  value       = module.rds.db_instance_address
  sensitive   = true
}

output "db_instance_name" {
  description = "Database name"
  value       = module.rds.db_instance_name
}

output "db_instance_username" {
  description = "Master username"
  value       = module.rds.db_instance_username
  sensitive   = true
}

output "db_instance_arn" {
  description = "RDS instance ARN"
  value       = module.rds.db_instance_arn
}

# output "db_master_user_secret_arn" {
#   description = "ARN of the master user secret in Secrets Manager"
#   # value       = module.rds.db_instance_master_user_secret_arn
#     value = module.rds.master_user_secret[0].secret_arn  
#   sensitive   = true
# }