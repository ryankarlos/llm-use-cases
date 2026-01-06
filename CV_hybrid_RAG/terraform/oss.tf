# OpenSearch Serverless for GraphRAG Vector Store
# This creates the vector store required for the lexical graph embeddings

locals {
  collection_name = "cv-vectors-${var.env}"
}

# OpenSearch Serverless Collection
resource "aws_opensearchserverless_collection" "vectors" {
  name        = local.collection_name
  type        = "VECTORSEARCH"
  description = "Vector store for CV matcher GraphRAG"

  depends_on = [
    aws_opensearchserverless_security_policy.encryption,
    aws_opensearchserverless_security_policy.network,
    aws_opensearchserverless_access_policy.data
  ]

  tags = {
    Name        = local.collection_name
    Environment = var.env
    Purpose     = "GraphRAG vector store"
  }
}

# Encryption Policy (required)
resource "aws_opensearchserverless_security_policy" "encryption" {
  name = "${local.collection_name}-encryption"
  type = "encryption"

  policy = jsonencode({
    Rules = [
      {
        Resource     = ["collection/${local.collection_name}"]
        ResourceType = "collection"
      }
    ]
    AWSOwnedKey = true
  })
}

# Network Policy
resource "aws_opensearchserverless_security_policy" "network" {
  name = "${local.collection_name}-network"
  type = "network"

  policy = jsonencode([
    {
      Rules = [
        {
          Resource     = ["collection/${local.collection_name}"]
          ResourceType = "collection"
        }
      ]
      AllowFromPublic = true
    }
  ])
}

# Data Access Policy
resource "aws_opensearchserverless_access_policy" "data" {
  name = "${local.collection_name}-access"
  type = "data"

  policy = jsonencode([
    {
      Rules = [
        {
          Resource     = ["collection/${local.collection_name}"]
          ResourceType = "collection"
          Permission   = ["aoss:CreateCollectionItems", "aoss:DeleteCollectionItems", "aoss:UpdateCollectionItems", "aoss:DescribeCollectionItems"]
        },
        {
          Resource     = ["index/${local.collection_name}/*"]
          ResourceType = "index"
          Permission   = ["aoss:CreateIndex", "aoss:DeleteIndex", "aoss:UpdateIndex", "aoss:DescribeIndex", "aoss:ReadDocument", "aoss:WriteDocument"]
        }
      ]
      Principal = var.allowed_principals
    }
  ])
}

# IAM Policy for accessing OpenSearch Serverless
resource "aws_iam_policy" "opensearch_access" {
  name        = "cv-matcher-opensearch-access-${var.env}"
  description = "Policy for accessing OpenSearch Serverless vector store"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "aoss:APIAccessAll"
        ]
        Resource = aws_opensearchserverless_collection.vectors.arn
      }
    ]
  })
}
