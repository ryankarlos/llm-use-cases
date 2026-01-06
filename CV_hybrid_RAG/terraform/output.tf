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
