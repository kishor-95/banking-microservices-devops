terraform {

backend "s3" {
    bucket         = "eks-cluster-tf-state-bucket-03-2026 "
    key            = "eks-rds/terraform.tfstate"
    region         = "ap-south-1"
    encrypt        = true
    use_lockfile   =  true
  }
}