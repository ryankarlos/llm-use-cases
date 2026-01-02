locals {
  opensearch_url = module.oss_kb.oss_endpoint
}

provider "opensearch" {
  url               = local.opensearch_url
  healthcheck       = false
  aws_region        = data.aws_region.current.region
  sniff             = false
  sign_aws_requests = true
}


module "s3_kb" {
  source = "git::https://github.com/terraform-aws-modules/terraform-aws-s3-bucket.git?ref=v5.1.0"

  bucket              = var.s3_bucket
  allowed_kms_key_arn = module.kms_s3.key_arn


  server_side_encryption_configuration = {
    rule = {
      apply_server_side_encryption_by_default = {
        kms_master_key_id = module.kms_s3.key_id
        sse_algorithm     = "aws:kms"
      }
    }
  }

}


resource "aws_s3_object" "kb_folder" {
  bucket  = module.s3_kb.s3_bucket_id
  key     = "knowledge-base/"
  content = ""
}

resource "aws_s3_object" "kb_data_upload" {
  for_each = toset(fileset(var.kb_data_path, "*.csv"))
  bucket   = module.s3_kb.s3_bucket_id
  key      = "knowledge-base/${each.value}"
  source   = "${var.kb_data_path}/${each.value}"
  etag     = filemd5("${var.kb_data_path}/${each.value}")
}

# Knowledge Base IAM Policy
resource "aws_iam_policy" "knowledge_base_policy" {
  name = "knowledge-base-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Embedding model access
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = var.bedrock_embedding_model_arn
      },

      # REQUIRED: Permission for OpenSearch Serverless collection
      {
        Effect = "Allow"
        Action = [
          "aoss:APIAccessAll"
        ]
        Resource = module.oss_kb.oss_collection_arn
      },

      # REQUIRED: Permission for the index inside the collection
      {
        Effect = "Allow"
        Action = [
          "aoss:APIAccessAll"
        ]
        Resource = "arn:aws:aoss:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:index/knowledge-base/*"
      },

      # S3 data source
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          module.s3_kb.s3_bucket_arn,
          "${module.s3_kb.s3_bucket_arn}/*"
        ]
      },

      # KMS decrypt for S3 bucket encryption
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey",
          "kms:GenerateDataKey"
        ]
        Resource = module.kms_s3.key_arn
      }
    ]
  })
}


# Knowledge Base IAM Role
resource "aws_iam_role" "knowledge_base_role" {
  name = "knowledge-base-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "bedrock.amazonaws.com"
        }
      }
    ]
  })
}


resource "aws_iam_role_policy_attachment" "knowledge_base_policy_attachment" {
  role       = aws_iam_role.knowledge_base_role.name
  policy_arn = aws_iam_policy.knowledge_base_policy.arn
}


module "kb" {
  source                                   = "github.com/ryankarlos/terraform_modules.git//aws/bedrock/kb"
  vpc_id                                   = data.aws_vpc.main.id
  vpc_endpoint_security_group_id           = data.aws_security_group.endpoint_security_group.id
  endpoint_subnet_ids                      = local.az_subnet_ids.endpoint
  security_group_id                        = data.aws_security_group.workload_security_group.id
  bedrock_embedding_model_arn              = var.bedrock_embedding_model_arn
  knowledge_base_name                      = "knowledge-base"
  kb_role_arn                              = aws_iam_role.knowledge_base_role.arn
  chunking_strategy                        = var.chunking_strategy
  semantic_max_tokens                      = var.semantic_max_tokens
  semantic_buffer_size                     = var.semantic_buffer_size
  semantic_breakpoint_percentile_threshold = var.semantic_breakpoint_percentile_threshold
  vector_dimension                         = var.vector_dimension
  data_source_bucket_arn                   = module.s3_kb.s3_bucket_arn
  data_source_prefix                       = "knowledge-base/"
  data_source_name                         = "knowledge-base-data-source"
  oss_collection_arn                       = module.oss_kb.oss_collection_arn
  oss_collection_name                      = "knowledge-base"
  vector_index_name                        = var.vector_index_name
}



module "oss_kb" {
  source                         = "github.com/ryankarlos/terraform_modules.git//aws/bedrock/oss"
  vpc_id                         = data.aws_vpc.main.id
  vpc_endpoint_security_group_id = data.aws_security_group.endpoint_security_group.id
  endpoint_subnet_ids            = local.az_subnet_ids.endpoint
  security_group_id              = data.aws_security_group.workload_security_group.id
  oss_collection_name            = "knowledge-base"
  number_of_shards               = var.number_of_shards
  number_of_replicas             = var.number_of_replicas
  vector_index_name              = var.vector_index_name
  index_knn                      = var.index_knn
  index_knn_algo_param_ef_search = var.index_knn_algo_param_ef_search
  knowledge_base_role_arn        = aws_iam_role.knowledge_base_role.arn
}

resource "aws_ssm_parameter" "knowledge_base_id" {
  # checkov:skip=CKV2_AWS_34
  name  = "kb-id-${var.env}-knowledge-base"
  type  = "String"
  value = module.kb.kb_id
}



resource "aws_ssm_parameter" "kb_id_manual" {
  # checkov:skip=CKV2_AWS_34
  name  = "kb-id-${var.env}-manual"
  type  = "String"
  value = var.kb_id_manual
}



# OpenSearch index creation
resource "opensearch_index" "resource_kb" {
  name                           = "bedrock-knowledge-base-default-index"
  number_of_shards               = "2"
  number_of_replicas             = "0"
  index_knn                      = true
  index_knn_algo_param_ef_search = "512"
  mappings                       = <<-EOF
    {
      "properties": {
        "bedrock-knowledge-base-default-vector": {
          "type": "knn_vector",
          "dimension": 1024,
          "method": {
            "name": "hnsw",
            "engine": "faiss",
            "parameters": {
              "m": 16,
              "ef_construction": 512
            },
            "space_type": "l2"
          }
        },
        "AMAZON_BEDROCK_METADATA": {
          "type": "text",
          "index": "false"
        },
        "AMAZON_BEDROCK_TEXT_CHUNK": {
          "type": "text",
          "index": "true"
        }
      }
    }
  EOF
  force_destroy                  = true
  depends_on                     = [module.oss_kb]
}
