locals {
  az_subnet_ids = {
    workload = flatten([
      for az, subnets in data.aws_subnets.workload_subnet : subnets.ids
    ])
    endpoint = flatten([
      for az, subnets in data.aws_subnets.endpoint_subnet : subnets.ids
    ])
  }
  litellm_config_path = "${var.litellm_dir}/${var.litellm_config_name}"
  serverless_instances = {
    1 = {
      instance_class                  = "db.serverless"
      engine_version                  = "9.16.1"
      performance_insights_enabled    = var.performance_insights_enabled
      performance_insights_kms_key_id = var.performance_insights_kms_key_id
    }
  }


}


module "litellm_secrets" {
  source       = "github.com/ryankarlos/terraform_modules.git//aws/secret"
  secret_type  = "key-value"
  secret_name  = var.litellm_secret_name
  secret_value = var.litellm_secret_values
  account_id   = data.aws_caller_identity.current.account_id
}



module "litellm_aurora_secret" {
  source      = "github.com/ryankarlos/terraform_modules.git//aws/secret"
  secret_type = "key-value"
  secret_name = "litellm-aurora-secret"
  secret_value = jsonencode({
    DATABASE_URL = "postgresql://${module.aurora_db.cluster_master_username}:${module.aurora_db.cluster_master_password}@${module.aurora_db.cluster_endpoint}:${tostring(module.aurora_db.cluster_port)}"
  })
  account_id              = data.aws_caller_identity.current.account_id
  recovery_window_in_days = 0
  key_deletion_window     = 7
}


module "litellm_redis_secret" {
  source      = "github.com/ryankarlos/terraform_modules.git//aws/secret"
  secret_type = "key-value"
  secret_name = "litellm-redis-secret"
  secret_value = jsonencode({
    REDIS_PASSWORD = "${random_password.redis_password_main.result}"
  })
  account_id              = data.aws_caller_identity.current.account_id
  recovery_window_in_days = 0
  key_deletion_window     = 7
}


resource "aws_ssm_parameter" "litellm_redis_host" {
  name   = "/${var.env}/valkey/litellm-redis-host"
  type   = "SecureString"
  value  = module.elasticache.replication_group_primary_endpoint_address
  key_id = aws_kms_key.valkey_kms.arn
}


## no pii so ss3-s3 encryption is ok.
module "s3_lb_logs" {
  source = "git::https://github.com/terraform-aws-modules/terraform-aws-s3-bucket.git?ref=v5.1.0"

  bucket              = var.s3_buckets.lb_access_logs
  allowed_kms_key_arn = module.kms_s3.key_arn


  server_side_encryption_configuration = {
    rule = {
      apply_server_side_encryption_by_default = {
        sse_algorithm = "AES256"
      }
    }
  }

}


module "s3_litellm_config" {
  source = "git::https://github.com/terraform-aws-modules/terraform-aws-s3-bucket.git?ref=v5.1.0"

  bucket = var.s3_buckets.litellm

  server_side_encryption_configuration = {
    rule = {
      apply_server_side_encryption_by_default = {
        kms_master_key_id = module.kms_s3.key_id
        sse_algorithm     = "aws:kms"
      }
    }
  }

}


module "bedrock" {
  source                         = "github.com/ryankarlos/terraform_modules.git//aws/bedrock"
  vpc_id                         = data.aws_vpc.main.id
  vpc_endpoint_security_group_id = data.aws_security_group.endpoint_security_group.id
  endpoint_subnet_ids            = local.az_subnet_ids.endpoint
  security_group_id              = data.aws_security_group.workload_security_group.id
}



# Random passwords for redis and db to be stored in secret manager
resource "random_password" "redis_password_main" {
  length  = 18
  special = false
}

resource "random_password" "aurora_password_main" {
  length  = 16
  special = false
}


# Subnet group for the DB
resource "aws_db_subnet_group" "aurora_subnet_group" {
  name       = "aurora-subnet-group"
  subnet_ids = local.az_subnet_ids.workload
}


module "aurora_db" {
  source            = "git::https://github.com/terraform-aws-modules/terraform-aws-rds-aurora.git?ref=v9.16.1"
  name              = "litellm-aurora-postgresql"
  engine            = "aurora-postgresql"
  engine_mode       = "provisioned"
  instance_class    = "db_serverless"
  instances         = local.serverless_instances
  storage_encrypted = true
  master_username   = "postgres"

  vpc_id               = data.aws_vpc.main.id
  db_subnet_group_name = aws_db_subnet_group.aurora_subnet_group.name
  security_group_rules = {
    vpc_ingress = {
      cidr_blocks = [var.ingress_cidr_range]

    }
  }

  manage_master_user_password        = false
  master_password                    = random_password.aurora_password_main.result
  monitoring_interval                = 60
  preferred_maintenance_window       = var.maintenance_window
  skip_final_snapshot                = var.skip_final_snapshot
  serverlessv2_scaling_configuration = var.aurora_scaling_config

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}

module "elasticache" {
  source         = "git::https://github.com/terraform-aws-modules/terraform-aws-elasticache.git?ref=v1.10.3"
  engine         = "valkey"
  engine_version = var.engine_version
  node_type      = var.node_type

  # Cluster mode enabled settings
  cluster_mode            = var.cluster_mode
  cluster_mode_enabled    = var.cluster_mode_enabled
  num_node_groups         = var.num_node_groups
  replicas_per_node_group = var.replicas_per_node_group

  # Multi-AZ & Automatic failover
  multi_az_enabled           = var.multi_az_enabled
  num_cache_clusters         = var.num_cache_clusters
  automatic_failover_enabled = var.automatic_failover_enabled

  # Cluster configuration
  transit_encryption_enabled = var.transit_encryption_enabled
  auth_token                 = random_password.redis_password_main.result
  maintenance_window         = var.maintenance_window
  apply_immediately          = var.apply_immediately
  at_rest_encryption_enabled = true
  kms_key_arn                = aws_kms_key.valkey_kms.arn


  # Replication Group
  create_replication_group = var.create_replication_group
  replication_group_id     = var.replication_group_id

  # Security Group
  vpc_id = data.aws_vpc.main.id
  security_group_rules = {
    ingress_vpc = {
      # Default type is `ingress`
      # Default port is based on the default engine port
      description = "VPC traffic"
      cidr_ipv4   = var.ingress_cidr_range
    }
  }

  # Subnet Group
  subnet_group_name        = var.subnet_group_name
  subnet_group_description = "Valkey replication group subnet group for ${var.env}"
  subnet_ids               = local.az_subnet_ids.workload

  # Parameter Group
  create_parameter_group      = var.create_parameter_group
  parameter_group_name        = var.parameter_group_name
  parameter_group_family      = var.parameter_group_family
  parameter_group_description = "Valkey replication group parameter group for ${var.env}"
  parameters                  = var.parameter_list

  # Tags
  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}


resource "aws_acm_certificate" "corp_cert" {
  private_key      = file(var.cert_pk)
  certificate_body = file(var.cert_body)
  lifecycle {
    create_before_destroy = true
  }
}
