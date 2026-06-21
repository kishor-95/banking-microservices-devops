terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.42.0"
    }

    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.13"
    }

    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.27"
    }

    time = {
      source  = "hashicorp/time"
      version = "~> 0.10"
    }
  }

  # Cloud configuration (optional - remove if not using Terraform Cloud)
  # cloud {
  #   organization = "your-org"
  #   workspaces {
  #     name = "banking-eks"
  #   }
  # }
}
