output "iam_role_arn" {
  description = "IAM role ARN for AWS Load Balancer Controller"
  value       = module.aws_load_balancer_controller_irsa.iam_role_arn
}

output "iam_role_name" {
  description = "IAM role name for AWS Load Balancer Controller"
  value       = module.aws_load_balancer_controller_irsa.iam_role_name
}

output "helm_release_id" {
  description = "Helm release ID"
  value       = try(helm_release.aws_load_balancer_controller[0].id, null)
}

output "helm_release_name" {
  description = "Helm release name"
  value       = try(helm_release.aws_load_balancer_controller[0].name, null)
}

output "helm_release_namespace" {
  description = "Helm release namespace"
  value       = try(helm_release.aws_load_balancer_controller[0].namespace, null)
}

output "helm_release_status" {
  description = "Helm release status"
  value       = try(helm_release.aws_load_balancer_controller[0].status, "disabled")
}

output "helm_release_version" {
  description = "Helm release version"
  value       = try(helm_release.aws_load_balancer_controller[0].version, null)
}

output "ingress_namespace" {
  description = "Kubernetes namespace for ingresses"
  value       = try(kubernetes_namespace_v1.ingress_ns[0].metadata[0].name, null)
}
