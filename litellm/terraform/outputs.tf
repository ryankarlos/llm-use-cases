
output "aurora_cluster_arn" {
  description = "aurora cluster arn"
  value       = module.aurora_db.cluster_arn
}

output "aurora_cluster_endpoint" {
  description = "Writer endpoint for the cluster"
  value       = module.aurora_db.cluster_endpoint
}


output "aurora_cluster_reader_endpoint" {
  description = "A read-only endpoint for the cluster, automatically load-balanced across replicas"
  value       = module.aurora_db.cluster_reader_endpoint
}



output "cert_secret_arn" {
  description = "cert secret arn"
  value       = module.corp_cert_secret.secret_arn
}


output "litellm_main_secret_arn" {
  description = "litellm main secret arn"
  value       = module.litellm_secrets.secret_arn
}



output "litellm_redis_secret_arn" {
  description = "litellm redis secret arn"
  value       = module.litellm_redis_secret.secret_arn
}


output "litellm_aurora_secret_arn" {
  description = "litellm aurora secret arn"
  value       = module.litellm_aurora_secret.secret_arn
}

