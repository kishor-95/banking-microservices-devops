# =============================================================================
# MANUAL SETUP REQUIRED
# =============================================================================
# 
# Before running terraform init, execute:
#
# 1. Create S3 bucket for remote state:
#    aws s3api create-bucket \
#      --bucket banking-eks-tf-state-dev-$(aws sts get-caller-identity --query Account --output text) \
#      --region ap-south-1 \
#      --create-bucket-configuration LocationConstraint=ap-south-1
#
# 2. Create DynamoDB table for state locking:
#    aws dynamodb create-table \
#      --table-name banking-eks-tf-locks-dev \
#      --attribute-definitions AttributeName=LockID,AttributeType=S \
#      --key-schema AttributeName=LockID,KeyType=HASH \
#      --billing-mode PAY_PER_REQUEST \
#      --region ap-south-1
#
# 3. Enable versioning on S3 bucket:
#    aws s3api put-bucket-versioning \
#      --bucket banking-eks-tf-state-dev-$(aws sts get-caller-identity --query Account --output text) \
#      --versioning-configuration Status=Enabled \
#      --region ap-south-1
#
# 4. Enable encryption on S3 bucket:
#    aws s3api put-bucket-encryption \
#      --bucket banking-eks-tf-state-dev-$(aws sts get-caller-identity --query Account --output text) \
#      --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}' \
#      --region ap-south-1
#
# After creating infrastructure manually, update the bucket name in backend.tf below.
# =============================================================================

terraform {
  backend "s3" {
    # Update this with your actual bucket name from manual setup
    bucket       = "banking-eks-cluster-dev-2026-6-3"
    key          = "banking-eks/dev/terraform.tfstate"
    region       = "ap-south-1"
    encrypt      = true
    use_lockfile = true
  }
}
