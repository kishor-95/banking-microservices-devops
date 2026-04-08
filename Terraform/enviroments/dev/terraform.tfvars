# AWS Configuration
aws_region   = "ap-south-1"
project_name = "banking-microservice"
environment  = "dev"

# VPC Configuration
vpc_cidr           = "10.0.0.0/16"
single_nat_gateway = true  # Cost optimization - change to false for HA

# EKS Configuration
cluster_name        = "banking-eks"
cluster_version     = "1.33"
node_instance_types = ["c7i-flex.large"]
node_min_size       = 1
node_max_size       = 3
node_desired_size   = 2

# Bastion Configuration
bastion_instance_type = "t3.small"
ec2_key_name          = "kishor-devops"  # CHANGE THIS to your EC2 key pair
allowed_ssh_cidr_blocks = [
  "0.0.0.0/0"  # CHANGE THIS to your IP address
]

# RDS Configuration
db_engine_version          = "17.6"
db_instance_class          = "db.t3.micro"
db_allocated_storage       = 20
db_max_allocated_storage   = 50
db_name                    = "bankapp"
db_username                = "dbadmin"      
db_backup_retention_period = 1                                            ## Chanage it 
db_deletion_protection     = true
db_skip_final_snapshot     = true  # Set to true for dev/testing only