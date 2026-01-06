resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_kms_key" "valkey_kms" {
  description         = "KMS CMK for ElastiCache Valkey - ${var.replication_group_id}"
  enable_key_rotation = true
}

resource "aws_kms_alias" "this" {
  name          = "alias/valkey-${var.replication_group_id}-${random_id.suffix.hex}"
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
    resources = [aws_kms_key.valkey_kms.arn]
  }
  statement {
    sid    = "CIRunnerAccess"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/ci-runner-role"]
    }
    actions = [
      "kms:Update*",
      "kms:UntagResource",
      "kms:TagResource",
      "kms:ScheduleKeyDeletion",
      "kms:Revoke*",
      "kms:ReplicateKey",
      "kms:Put*",
      "kms:List*",
      "kms:ImportKeyMaterial",
      "kms:Get*",
      "kms:Enable*",
      "kms:Disable*",
      "kms:Describe*",
      "kms:Delete*",
      "kms:Create*",
      "kms:CancelKeyDeletion"
    ]
    resources = [aws_kms_key.valkey_kms.arn]
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
    resources = [aws_kms_key.valkey_kms.arn]
    condition {
      test     = "StringEquals"
      variable = "kms:CallerAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
  statement {
    sid    = "AWSEKSResourcePolicy"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["eks.amazonaws.com"]
    }
    actions = [
      "kms:Decrypt",
      "kms:DescribeKey"
    ]
    resources = [aws_kms_key.valkey_kms.arn]
    condition {
      test     = "StringEquals"
      variable = "kms:CallerAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}



module "kms_s3" {
  source = "git::https://github.com/terraform-aws-modules/terraform-aws-kms.git"

  description             = "S3 kms CMK"
  key_usage               = "ENCRYPT_DECRYPT"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  # Aliases
  aliases = ["${var.project_name}/s3"]

}