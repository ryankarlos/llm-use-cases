
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
  value       = module.litellm_secrets.secret_arn
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



# CloudFront outputs
output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = aws_cloudfront_distribution.main.id
}

output "cloudfront_distribution_domain_name" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.main.domain_name
}

output "cloudfront_distribution_arn" {
  description = "CloudFront distribution ARN"
  value       = aws_cloudfront_distribution.main.arn
}


output "cloudfront_route53_fqdn" {
  description = "Route53 FQDN for CloudFront distribution"
  value       = aws_route53_record.cloudfront.fqdn
}


# Bedrock Guardrail outputs
output "bedrock_guardrail_id" {
  description = "Bedrock Guardrail ID"
  value       = aws_bedrock_guardrail.content_filter.guardrail_id
}

output "bedrock_guardrail_arn" {
  description = "Bedrock Guardrail ARN"
  value       = aws_bedrock_guardrail.content_filter.guardrail_arn
}

output "bedrock_guardrail_version" {
  description = "Bedrock Guardrail Version"
  value       = aws_bedrock_guardrail_version.content_filter.version
}
