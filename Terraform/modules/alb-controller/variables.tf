variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
}

variable "cluster_oidc_provider_arn" {
  description = "EKS OIDC provider ARN for IRSA"
  type        = string

  validation {
    condition     = can(regex("^arn:aws:iam::", var.cluster_oidc_provider_arn))
    error_message = "Must be a valid IAM ARN."
  }
}

variable "chart_version" {
  description = "AWS Load Balancer Controller Helm chart version"
  type        = string
  default     = "2.7.0"

  validation {
    condition     = can(regex("^[0-9]+\\.[0-9]+\\.[0-9]+$", var.chart_version))
    error_message = "Chart version must be in X.Y.Z format (e.g., 2.7.0)."
  }
}

variable "enable_deployment" {
  description = "Enable deployment of AWS Load Balancer Controller"
  type        = bool
  default     = true
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# variable "depends_on" {
#   description = "Explicit dependencies for Helm release"
#   type        = list(any)
#   default     = []
# }
