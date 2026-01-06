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
  source = "git::https://github.com/terraform-aws-modules/terraform-aws-s3-bucket.git"

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
  source = "git::https://github.com/terraform-aws-modules/terraform-aws-s3-bucket.git"

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
  source            = "git::https://github.com/terraform-aws-modules/terraform-aws-rds-aurora.git"
  name              = "litellm-aurora-postgresql"
  engine            = "aurora-postgresql"
  engine_mode       = "provisioned"
  instances         = local.serverless_instances
  storage_encrypted = true
  master_username   = "postgres"

  vpc_id               = data.aws_vpc.main.id
  db_subnet_group_name = aws_db_subnet_group.aurora_subnet_group.name
  security_group_ingress_rules = {
    vpc_ingress = {
      cidr_ipv4 = var.ingress_cidr_range
    }
  }

  manage_master_user_password        = false
  master_password_wo                 = random_password.aurora_password_main.result
  cluster_monitoring_interval        = 60
  preferred_maintenance_window       = var.maintenance_window
  skip_final_snapshot                = var.skip_final_snapshot
  serverlessv2_scaling_configuration = var.aurora_scaling_config

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}

module "elasticache" {
  source         = "git::https://github.com/terraform-aws-modules/terraform-aws-elasticache.git"
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


resource "aws_acm_certificate" "litellm_cert" {
  private_key      = file(var.cert_pk)
  certificate_body = file(var.cert_body)
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_s3_object" "file_upload" {
  bucket      = module.s3_litellm_config.s3_bucket_id
  key         = var.litellm_config_name
  source      = local.litellm_config_path
  source_hash = filemd5(local.litellm_config_path)
}


module "route_53_records_litellm" {
  source           = "github.com/ryankarlos/terraform_modules.git//aws/route_53/alias_record"
  hosted_zone_name = var.hosted_zone_name
  subdomain        = var.subdomain
  alias_name       = module.load_balancer_litellm.dns
  alias_zone_id    = module.load_balancer_litellm.zone_id
}


module "acm_cert_litellm" {
  source                    = "github.com/ryankarlos/terraform_modules.git//aws/acm_certificate"
  certificate_authority_arn = var.certificate_authority_arn
  domain_name               = module.route_53_records_litellm.record_fqdn
}


resource "aws_lb_listener_certificate" "litellm_listener_cert" {
  listener_arn    = module.load_balancer_litellm.https_listener_arn
  certificate_arn = module.acm_cert_litellm.certificate_arn
}


module "load_balancer_litellm" {
  source                       = "github.com/ryankarlos/terraform_modules.git//aws/load_balancer/application/ip_target"
  vpc_id                       = data.aws_vpc.main.id
  subnet_ids                   = local.az_subnet_ids.workload
  certificate_arn              = module.acm_cert_litellm.certificate_arn
  security_group_id            = data.aws_security_group.workload_security_group.id
  alb_name                     = var.alb_name
  tag                          = var.tag
  target_group_port            = var.litellm_port
  target_group_name            = var.target_group_name
  enable_mutual_authentication = false
  health_check_path            = "/health/liveliness"
  enable_http_listener         = true
}




module "ecs_litellm" {
  source = "github.com/ryankarlos/terraform_modules.git//aws/ecs"

  cluster_name                    = "litellm-cluster"
  service_name                    = "litellm-service"
  container_name                  = "litellm-container"
  subnet_ids                      = local.az_subnet_ids.workload
  desired_count                   = var.desired_count
  min_capacity                    = var.min_capacity
  max_capacity                    = var.max_capacity
  launch_type                     = var.launch_type
  security_group_ids              = [data.aws_security_group.workload_security_group.id]
  task_execution_role_name        = "LitellmTaskExecutionRole"
  task_role_name                  = "LitellmTaskRole"
  enable_load_balancer            = true
  enable_circuit_breaker_rollback = true
  enable_circuit_breaker          = true

  container_definitions = jsonencode([
    {
      name      = "litellm-container"
      essential = true
      environment = [
        {
          name  = "AWS_REGION"
          value = data.aws_region.current.name
        },
        {
          name  = "LITELLM_LOG"
          value = var.litellm_log_level
        },
        {
          name  = "LITELLM_CONFIG_BUCKET_NAME"
          value = "${module.s3_litellm_config.s3_bucket_id}"
        },
        {
          name  = "LITELLM_CONFIG_BUCKET_OBJECT_KEY"
          value = var.litellm_config_name
        },
        {
          name  = "DATABASE_NAME"
          value = "${module.aurora_db.cluster_database_name}"
        },
        {
          name  = "DATABASE_HOST"
          value = "${module.aurora_db.cluster_endpoint}"
        },
        {
          name  = "DATABASE_PORT"
          value = "${tostring(module.aurora_db.cluster_port)}"
        },
        {
          name  = "DATABASE_USERNAME",
          value = "${module.aurora_db.cluster_master_username}"
        },

        {
          name  = "REDIS_HOST",
          value = "${module.elasticache.replication_group_primary_endpoint_address}"
        },
        {
          name  = "REDIS_PORT",
          value = "${tostring(var.redis_port)}"
        },
        {
          name  = "REDIS_PASSWORD",
          value = "${random_password.redis_password_main.result}"
        },
        {
          name  = "REDIS_SSL",
          value = "True"
        },
        {
          name  = "PHOENIX_API_KEY",
          value = var.phoenix_api_key
        },
        {
          name  = "PHOENIX_PROJECT_NAME",
          value = "litellm-demo"
        },
        {
          name  = "BEDROCK_GUARDRAIL_ID",
          value = aws_bedrock_guardrail.content_filter.guardrail_id
        },
        {
          name  = "BEDROCK_GUARDRAIL_VERSION",
          value = aws_bedrock_guardrail_version.content_filter.version
        }

      ],
      # this block fetches values from secret manager
      secrets = [
        {
          "name" : "LITELLM_MASTER_KEY",
          "valueFrom" : "${module.litellm_secrets.secret_arn}:LITELLM_MASTER_KEY::"
        },
        {
          "name" : "LITELLM_SALT_KEY",
          "valueFrom" : "${module.litellm_secrets.secret_arn}:LITELLM_SALT_KEY::"
        },
        {
          "name" : "UI_PASSWORD",
          "valueFrom" : "${module.litellm_secrets.secret_arn}:LITELLM_MASTER_KEY::"
        },

        {
          "name" : "DATABASE_URL",
          "valueFrom" : "${module.litellm_aurora_secret.secret_arn}:DATABASE_URL::"
        }
      ]
      image = var.image_uri_litellm
      portMappings = [{
        appProtocol   = "http"
        containerPort = var.litellm_port,
        hostPort      = var.litellm_port,
        protocol      = "tcp"
      }]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "demo-litellm"
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "ecs"
          "awslogs-create-group"  = "true"
          "mode" : "non-blocking",
        }
      }
  }])
  scaling_type     = "cpu"
  container_port   = var.litellm_port
  target_group_arn = module.load_balancer_litellm.target_group_arn
}
