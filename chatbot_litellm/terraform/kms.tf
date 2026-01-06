resource "random_id" "suffix" {
  byte_length = 4
}

locals {
  replication_group_name = coalesce(var.replication_group_id, "litellm-valkey")
}

resource "aws_kms_key" "valkey_kms" {
  description         = "KMS CMK for ElastiCache Valkey - ${local.replication_group_name}"
  enable_key_rotation = true
}

resource "aws_kms_alias" "this" {
  name          = "alias/valkey-${local.replication_group_name}-${random_id.suffix.hex}"
  target_key_id = aws_kms_key.valkey_kms.key_id
}


resource "aws_kms_key_policy" "this" {
  key_id = aws_kms_key.valkey_kms.id
  policy = data.aws_iam_policy_document.this.json
}

data "aws_iam_policy_document" "this" {
  statement {
    sid    = "RootAccess"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
    actions = [
      "kms:*"
    ]
    resources = ["*"]
  }
  statement {
    sid    = "AWSEC2ResourcePolicy"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
    actions = [
      "kms:Decrypt",
      "kms:DescribeKey"
    ]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "kms:CallerAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
  statement {
    sid    = "ElastiCacheServicePolicy"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["elasticache.amazonaws.com"]
    }
    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:DescribeKey",
      "kms:CreateGrant"
    ]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "kms:CallerAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}