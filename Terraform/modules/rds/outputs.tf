output "db_instance_id" {
  value = module.rds.db_instance_identifier
}

output "db_instance_arn" {
  value = module.rds.db_instance_arn
}

output "db_instance_endpoint" {
  value     = module.rds.db_instance_endpoint
  sensitive = true
}

output "db_instance_address" {
  value     = module.rds.db_instance_address
  sensitive = true
}

output "db_instance_port" {
  value = module.rds.db_instance_port
}

output "db_instance_name" {
  value = module.rds.db_instance_name
}

output "db_instance_username" {
  value     = module.rds.db_instance_username
  sensitive = true
}

output "master_user_secret_arn" {
  value     = module.rds.db_instance_master_user_secret_arn
  sensitive = true
}