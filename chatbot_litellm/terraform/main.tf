locals {
  # Use private subnets for workload resources
  private_subnet_ids = data.aws_subnets.private_subnets.ids
  # Use public subnets for ALB
  public_subnet_ids = data.aws_subnets.public_subnets.ids
  
  serverless_instances = {
    1 = {
      instance_class                  = "db.serverless"
      engine_version                  = "16.1"
      performance_insights_enabled    = var.performance_insights_enabled
      performance_insights_kms_key_id = var.performance_insights_kms_key_id
    }
  }
}

# =============================================================================
# Route53 Hosted Zone
# =============================================================================
resource "aws_route53_zone" "main" {
  name = var.hosted_zone_name

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}

# =============================================================================
# Self-Signed Certificate for ALB
# =============================================================================
resource "tls_private_key" "self_signed" {
  algorithm = "RSA"
  rsa_bits  = 2048
}

resource "tls_self_signed_cert" "self_signed" {
  private_key_pem = tls_private_key.self_signed.private_key_pem

  subject {
    common_name  = "${var.subdomain}.${var.hosted_zone_name}"
    organization = var.project_name
  }

  validity_period_hours = 8760 # 1 year

  allowed_uses = [
    "key_encipherment",
    "digital_signature",
    "server_auth",
  ]
}

resource "aws_acm_certificate" "self_signed" {
  private_key      = tls_private_key.self_signed.private_key_pem
  certificate_body = tls_self_signed_cert.self_signed.cert_pem

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}

# =============================================================================
# Secrets Manager (values to be populated after deployment)
# =============================================================================
resource "aws_secretsmanager_secret" "litellm_secrets" {
  name                    = var.litellm_secret_name
  recovery_window_in_days = 0

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}

resource "aws_secretsmanager_secret_version" "litellm_secrets" {
  secret_id     = aws_secretsmanager_secret.litellm_secrets.id
  secret_string = var.litellm_secret_values
}

resource "aws_secretsmanager_secret" "litellm_aurora_secret" {
  name                    = "litellm-aurora-secret"
  recovery_window_in_days = 0

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}

resource "aws_secretsmanager_secret_version" "litellm_aurora_secret" {
  secret_id = aws_secretsmanager_secret.litellm_aurora_secret.id
  secret_string = jsonencode({
    DATABASE_URL = "postgresql://${module.aurora_db.cluster_master_username}:${random_password.aurora_password_main.result}@${module.aurora_db.cluster_endpoint}:${tostring(module.aurora_db.cluster_port)}/postgres"
  })
}

resource "aws_secretsmanager_secret" "litellm_redis_secret" {
  name                    = "litellm-redis-secret"
  recovery_window_in_days = 0

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}

resource "aws_secretsmanager_secret_version" "litellm_redis_secret" {
  secret_id = aws_secretsmanager_secret.litellm_redis_secret.id
  secret_string = jsonencode({
    REDIS_PASSWORD = random_password.redis_password_main.result
  })
}

resource "aws_ssm_parameter" "litellm_redis_host" {
  name   = "/${var.env}/valkey/litellm-redis-host"
  type   = "SecureString"
  value  = module.elasticache.replication_group_primary_endpoint_address
  key_id = aws_kms_key.valkey_kms.arn
}

# =============================================================================
# Bedrock VPC Endpoints
# =============================================================================
module "bedrock" {
  source                         = "github.com/ryankarlos/terraform_modules.git//aws/bedrock"
  vpc_id                         = data.aws_vpc.main.id
  vpc_endpoint_security_group_id = data.aws_security_group.workload_security_group.id
  endpoint_subnet_ids            = local.private_subnet_ids
  security_group_id              = data.aws_security_group.workload_security_group.id
}

# =============================================================================
# Random Passwords
# =============================================================================
resource "random_password" "redis_password_main" {
  length  = 18
  special = false
}

resource "random_password" "aurora_password_main" {
  length  = 16
  special = false
}

# =============================================================================
# Aurora PostgreSQL
# =============================================================================
resource "aws_db_subnet_group" "aurora_subnet_group" {
  name       = "aurora-subnet-group"
  subnet_ids = local.private_subnet_ids
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
  master_password_wo_version         = 1
  cluster_monitoring_interval        = 60
  preferred_maintenance_window       = var.maintenance_window
  skip_final_snapshot                = var.skip_final_snapshot
  serverlessv2_scaling_configuration = var.aurora_scaling_config

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}


# =============================================================================
# ElastiCache (Valkey/Redis)
# =============================================================================
module "elasticache" {
  source         = "git::https://github.com/terraform-aws-modules/terraform-aws-elasticache.git"
  engine         = "valkey"
  engine_version = var.engine_version
  node_type      = var.node_type

  cluster_mode            = var.cluster_mode
  cluster_mode_enabled    = var.cluster_mode_enabled
  num_node_groups         = var.num_node_groups
  replicas_per_node_group = var.replicas_per_node_group

  multi_az_enabled           = var.multi_az_enabled
  num_cache_clusters         = var.num_cache_clusters
  automatic_failover_enabled = var.automatic_failover_enabled

  transit_encryption_enabled = var.transit_encryption_enabled
  auth_token                 = random_password.redis_password_main.result
  maintenance_window         = var.maintenance_window
  apply_immediately          = var.apply_immediately
  at_rest_encryption_enabled = true
  kms_key_arn                = aws_kms_key.valkey_kms.arn

  create_replication_group = var.create_replication_group
  replication_group_id     = "litellm-valkey"

  vpc_id = data.aws_vpc.main.id
  security_group_rules = {
    ingress_vpc = {
      description = "VPC traffic"
      cidr_ipv4   = var.ingress_cidr_range
    }
  }

  subnet_group_name        = var.subnet_group_name
  subnet_group_description = "Valkey replication group subnet group for ${var.env}"
  subnet_ids               = local.private_subnet_ids

  create_parameter_group      = var.create_parameter_group
  parameter_group_name        = var.parameter_group_name
  parameter_group_family      = var.parameter_group_family
  parameter_group_description = "Valkey replication group parameter group for ${var.env}"
  parameters                  = var.parameter_list

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}

# =============================================================================
# Route53 Record
# =============================================================================
resource "aws_route53_record" "litellm" {
  zone_id = aws_route53_zone.main.zone_id
  name    = var.subdomain
  type    = "A"

  alias {
    name                   = module.load_balancer_litellm.dns
    zone_id                = module.load_balancer_litellm.zone_id
    evaluate_target_health = true
  }
}

# =============================================================================
# Application Load Balancer
# =============================================================================
module "load_balancer_litellm" {
  source                       = "github.com/ryankarlos/terraform_modules.git//aws/load_balancer/application/ip_target"
  vpc_id                       = data.aws_vpc.main.id
  subnet_ids                   = local.public_subnet_ids
  certificate_arn              = aws_acm_certificate.self_signed.arn
  security_group_id            = data.aws_security_group.workload_security_group.id
  alb_name                     = var.alb_name
  tag                          = var.tag
  target_group_port            = var.litellm_port
  target_group_name            = var.target_group_name
  enable_mutual_authentication = false
  health_check_path            = "/health/liveliness"
  enable_http_listener         = true
}


# =============================================================================
# ECS Cluster and Service
# =============================================================================
module "ecs_litellm" {
  source = "github.com/ryankarlos/terraform_modules.git//aws/ecs"

  cluster_name                    = "litellm-cluster"
  service_name                    = "litellm-service"
  container_name                  = "litellm-container"
  subnet_ids                      = local.private_subnet_ids
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
          name  = "DATABASE_USERNAME"
          value = "${module.aurora_db.cluster_master_username}"
        },
        {
          name  = "REDIS_HOST"
          value = "${module.elasticache.replication_group_primary_endpoint_address}"
        },
        {
          name  = "REDIS_PORT"
          value = "${tostring(var.redis_port)}"
        },
        {
          name  = "REDIS_PASSWORD"
          value = "${random_password.redis_password_main.result}"
        },
        {
          name  = "REDIS_SSL"
          value = "True"
        },
        {
          name  = "PHOENIX_API_KEY"
          value = var.phoenix_api_key
        },
        {
          name  = "PHOENIX_PROJECT_NAME"
          value = "litellm-demo"
        },
        {
          name  = "BEDROCK_GUARDRAIL_ID"
          value = aws_bedrock_guardrail.content_filter.guardrail_id
        },
        {
          name  = "BEDROCK_GUARDRAIL_VERSION"
          value = aws_bedrock_guardrail_version.content_filter.version
        }
      ]
      secrets = [
        {
          "name" : "LITELLM_MASTER_KEY",
          "valueFrom" : "${aws_secretsmanager_secret.litellm_secrets.arn}:LITELLM_MASTER_KEY::"
        },
        {
          "name" : "LITELLM_SALT_KEY",
          "valueFrom" : "${aws_secretsmanager_secret.litellm_secrets.arn}:LITELLM_SALT_KEY::"
        },
        {
          "name" : "UI_PASSWORD",
          "valueFrom" : "${aws_secretsmanager_secret.litellm_secrets.arn}:LITELLM_MASTER_KEY::"
        },
        {
          "name" : "DATABASE_URL",
          "valueFrom" : "${aws_secretsmanager_secret.litellm_aurora_secret.arn}:DATABASE_URL::"
        }
      ]
      image = var.image_uri_litellm
      portMappings = [{
        appProtocol   = "http"
        containerPort = var.litellm_port
        hostPort      = var.litellm_port
        protocol      = "tcp"
      }]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "demo-litellm"
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "ecs"
          "awslogs-create-group"  = "true"
          "mode"                  = "non-blocking"
        }
      }
    }
  ])
  scaling_type     = "cpu"
  container_port   = var.litellm_port
  target_group_arn = module.load_balancer_litellm.target_group_arn
}
