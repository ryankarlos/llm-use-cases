# =============================================================================
# Aurora Outputs
# =============================================================================
output "aurora_cluster_arn" {
  description = "Aurora cluster ARN"
  value       = module.aurora_db.cluster_arn
}

output "aurora_cluster_endpoint" {
  description = "Writer endpoint for the cluster"
  value       = module.aurora_db.cluster_endpoint
}

output "aurora_cluster_reader_endpoint" {
  description = "Read-only endpoint for the cluster"
  value       = module.aurora_db.cluster_reader_endpoint
}

# =============================================================================
# Secrets Manager Outputs
# =============================================================================
output "litellm_master_salt_secret_arn" {
  description = "LiteLLM master/salt keys secret ARN"
  value       = aws_secretsmanager_secret.litellm_master_salt.arn
}

output "litellm_db_url_secret_arn" {
  description = "LiteLLM database URL secret ARN"
  value       = aws_secretsmanager_secret.litellm_db_url.arn
}

output "phoenix_api_key_secret_arn" {
  description = "Phoenix API key secret ARN"
  value       = aws_secretsmanager_secret.phoenix_api_key.arn
}

# =============================================================================
# ElastiCache Outputs
# =============================================================================
output "redis_endpoint" {
  description = "Redis/Valkey primary endpoint"
  value       = module.elasticache.replication_group_primary_endpoint_address
}

# =============================================================================
# ALB Outputs
# =============================================================================
output "alb_dns_name" {
  description = "ALB DNS name"
  value       = aws_lb.litellm.dns_name
}

output "alb_arn" {
  description = "ALB ARN"
  value       = aws_lb.litellm.arn
}

# =============================================================================
# WAF Outputs
# =============================================================================
output "waf_acl_arn" {
  description = "WAF Web ACL ARN"
  value       = aws_wafv2_web_acl.litellm.arn
}

output "waf_ip_whitelist_arn" {
  description = "WAF IP whitelist ARN"
  value       = aws_wafv2_ip_set.whitelist.arn
}

# =============================================================================
# Bedrock Guardrail Outputs
# =============================================================================
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

# =============================================================================
# ECS Outputs
# =============================================================================
output "ecs_cluster_arn" {
  description = "ECS cluster ARN"
  value       = aws_ecs_cluster.litellm.arn
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.litellm.name
}
