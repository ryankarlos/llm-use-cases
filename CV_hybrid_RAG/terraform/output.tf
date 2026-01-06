# OpenSearch Serverless outputs
output "opensearch_endpoint" {
  description = "OpenSearch Serverless collection endpoint"
  value       = aws_opensearchserverless_collection.vectors.collection_endpoint
}

output "opensearch_collection_arn" {
  description = "OpenSearch Serverless collection ARN"
  value       = aws_opensearchserverless_collection.vectors.arn
}

output "opensearch_dashboard_endpoint" {
  description = "OpenSearch Serverless dashboard endpoint"
  value       = aws_opensearchserverless_collection.vectors.dashboard_endpoint
}

# Neptune outputs
output "neptune_endpoint" {
  description = "Neptune cluster endpoint for GraphRAG"
  value       = aws_neptune_cluster.graphrag.endpoint
}

output "neptune_reader_endpoint" {
  description = "Neptune cluster reader endpoint"
  value       = aws_neptune_cluster.graphrag.reader_endpoint
}

output "neptune_port" {
  description = "Neptune cluster port"
  value       = aws_neptune_cluster.graphrag.port
}

# API outputs
output "api_endpoint" {
  description = "Lambda Function URL for CV Matcher API"
  value       = aws_lambda_function_url.cv_matcher.function_url
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.cv_matcher.function_name
}

output "ecr_repository_url" {
  description = "ECR repository URL for Lambda container"
  value       = aws_ecr_repository.cv_matcher.repository_url
}
