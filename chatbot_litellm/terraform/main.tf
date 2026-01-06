locals {
  public_subnet_ids = data.aws_subnets.public_subnets.ids
  config_hash       = filemd5("${path.module}/../config.yaml")
  dockerfile_hash   = filemd5("${path.module}/../Dockerfile.litellm")

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
# Docker Build and Push to ECR
# =============================================================================
resource "aws_ecr_repository" "litellm" {
  name                 = "litellm-base"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}

resource "null_resource" "docker_build_push" {
  triggers = {
    config_hash     = local.config_hash
    dockerfile_hash = local.dockerfile_hash
  }

  provisioner "local-exec" {
    working_dir = "${path.module}/.."
    command     = <<-EOT
      aws ecr get-login-password --region ${data.aws_region.current.name} | docker login --username AWS --password-stdin ${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com
      docker build -f Dockerfile.litellm -t ${aws_ecr_repository.litellm.repository_url}:latest .
      docker push ${aws_ecr_repository.litellm.repository_url}:latest
    EOT
  }

  depends_on = [aws_ecr_repository.litellm]
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
    common_name  = "litellm-gateway.local"
    organization = var.project_name
  }

  validity_period_hours = 8760

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
# Random Passwords (as per reference architecture)
# =============================================================================
resource "random_password" "litellm_master" {
  length  = 21
  special = false
}

resource "random_password" "litellm_salt" {
  length  = 21
  special = false
}

resource "random_password" "redis_password" {
  length  = 18
  special = false
}

resource "random_password" "aurora_password" {
  length  = 16
  special = false
}

# =============================================================================
# Secrets Manager - LiteLLM Master/Salt Keys (auto-generated with sk- prefix)
# =============================================================================
resource "aws_secretsmanager_secret" "litellm_master_salt" {
  name_prefix             = "${var.project_name}-master-salt-"
  recovery_window_in_days = 0

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}

resource "aws_secretsmanager_secret_version" "litellm_master_salt" {
  secret_id = aws_secretsmanager_secret.litellm_master_salt.id
  secret_string = jsonencode({
    LITELLM_MASTER_KEY = "sk-${random_password.litellm_master.result}"
    LITELLM_SALT_KEY   = "sk-${random_password.litellm_salt.result}"
  })
}

# =============================================================================
# Secrets Manager - Database URL (constructed from Aurora credentials)
# =============================================================================
resource "aws_secretsmanager_secret" "litellm_db_url" {
  name_prefix             = "${var.project_name}-db-url-"
  recovery_window_in_days = 0

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}

resource "aws_secretsmanager_secret_version" "litellm_db_url" {
  secret_id     = aws_secretsmanager_secret.litellm_db_url.id
  secret_string = "postgresql://${module.aurora_db.cluster_master_username}:${random_password.aurora_password.result}@${module.aurora_db.cluster_endpoint}:${tostring(module.aurora_db.cluster_port)}/postgres"
}

# =============================================================================
# Secrets Manager - Phoenix API Key
# =============================================================================
resource "aws_secretsmanager_secret" "phoenix_api_key" {
  name_prefix             = "${var.project_name}-phoenix-api-key-"
  recovery_window_in_days = 0

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}

resource "aws_secretsmanager_secret_version" "phoenix_api_key" {
  secret_id     = aws_secretsmanager_secret.phoenix_api_key.id
  secret_string = var.phoenix_api_key
}

# =============================================================================
# Secrets Manager - LiteLLM API Key (for Lambda/external access)
# =============================================================================
resource "aws_secretsmanager_secret" "litellm_api_key" {
  name_prefix             = "${var.project_name}-litellm-api-key-"
  recovery_window_in_days = 0

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}

resource "aws_secretsmanager_secret_version" "litellm_api_key" {
  secret_id     = aws_secretsmanager_secret.litellm_api_key.id
  secret_string = var.litellm_api_key
}


# =============================================================================
# Aurora PostgreSQL
# =============================================================================
resource "aws_db_subnet_group" "aurora" {
  name       = "${var.project_name}-aurora-subnet-group"
  subnet_ids = local.database_subnet_ids

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}

module "aurora_db" {
  source            = "git::https://github.com/terraform-aws-modules/terraform-aws-rds-aurora.git"
  name              = "${var.project_name}-aurora-postgresql"
  engine            = "aurora-postgresql"
  engine_mode       = "provisioned"
  instances         = local.serverless_instances
  storage_encrypted = true
  master_username   = "postgres"

  vpc_id               = data.aws_vpc.main.id
  db_subnet_group_name = aws_db_subnet_group.aurora.name
  security_group_ingress_rules = {
    vpc_ingress = {
      cidr_ipv4 = var.ingress_cidr_range
    }
  }

  manage_master_user_password        = false
  master_password_wo                 = random_password.aurora_password.result
  master_password_wo_version         = 1
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

  multi_az_enabled           = var.multi_az_enabled
  num_cache_clusters         = var.num_cache_clusters
  automatic_failover_enabled = var.automatic_failover_enabled

  transit_encryption_enabled = var.transit_encryption_enabled
  auth_token                 = random_password.redis_password.result
  maintenance_window         = var.maintenance_window
  apply_immediately          = var.apply_immediately
  at_rest_encryption_enabled = true

  create_replication_group = var.create_replication_group
  replication_group_id     = "${var.project_name}-valkey"

  vpc_id = data.aws_vpc.main.id
  security_group_rules = {
    ingress_vpc = {
      description = "VPC traffic"
      cidr_ipv4   = var.ingress_cidr_range
    }
  }

  subnet_group_name        = "${var.project_name}-valkey-subnet"
  subnet_group_description = "Valkey subnet group for ${var.env}"
  subnet_ids               = local.database_subnet_ids

  create_parameter_group      = var.create_parameter_group
  parameter_group_family      = var.parameter_group_family
  parameter_group_description = "Valkey parameter group for ${var.env}"
  parameters                  = var.parameter_list

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}


# =============================================================================
# WAFv2 IP Set for Whitelist
# =============================================================================
resource "aws_wafv2_ip_set" "whitelist" {
  name               = "${var.project_name}-ip-whitelist"
  description        = "Whitelisted IP addresses"
  scope              = "REGIONAL"
  ip_address_version = "IPV4"
  addresses          = var.waf_whitelisted_ips

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}

# =============================================================================
# WAFv2 Web ACL for ALB
# =============================================================================
resource "aws_wafv2_web_acl" "litellm" {
  name        = "${var.project_name}-waf"
  description = "WAF for LiteLLM ALB with IP whitelist and DDoS protection"
  scope       = "REGIONAL"

  default_action {
    block {}
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.project_name}-waf"
    sampled_requests_enabled   = true
  }

  # Priority 0: Allow whitelisted IPs
  rule {
    name     = "AllowWhitelistedIPs"
    priority = 0

    action {
      allow {}
    }

    statement {
      ip_set_reference_statement {
        arn = aws_wafv2_ip_set.whitelist.arn
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.project_name}-whitelist"
      sampled_requests_enabled   = true
    }
  }

  # Priority 1: Rate-based rule for DDoS protection
  rule {
    name     = "RateLimitRule"
    priority = 1

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = var.waf_rate_limit
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.project_name}-rate-limit"
      sampled_requests_enabled   = true
    }
  }

  # Priority 2: AWS Managed Rules - Common Rule Set
  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"

        rule_action_override {
          name = "NoUserAgent_HEADER"
          action_to_use {
            count {}
          }
        }

        rule_action_override {
          name = "SizeRestrictions_BODY"
          action_to_use {
            count {}
          }
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.project_name}-common-rules"
      sampled_requests_enabled   = true
    }
  }

  # Priority 3: AWS Managed Rules - Known Bad Inputs
  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 3

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.project_name}-bad-inputs"
      sampled_requests_enabled   = true
    }
  }

  # Priority 4: AWS Managed Rules - IP Reputation List (blocks known malicious IPs)
  rule {
    name     = "AWSManagedRulesAmazonIpReputationList"
    priority = 4

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesAmazonIpReputationList"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.project_name}-ip-reputation"
      sampled_requests_enabled   = true
    }
  }

  # Priority 5: AWS Managed Rules - Anonymous IP List (blocks VPNs, proxies, Tor)
  rule {
    name     = "AWSManagedRulesAnonymousIpList"
    priority = 5

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesAnonymousIpList"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.project_name}-anonymous-ip"
      sampled_requests_enabled   = true
    }
  }

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}

# =============================================================================
# Security Groups
# =============================================================================
resource "aws_security_group" "alb" {
  name        = "${var.project_name}-alb-sg"
  description = "Security group for ALB - restricted to allowed IPs"
  vpc_id      = data.aws_vpc.main.id

  ingress {
    description = "HTTPS from allowed IPs"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  ingress {
    description = "HTTP from allowed IPs"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-alb-sg"
    Project     = var.project_name
    Environment = var.env
  }
}

resource "aws_security_group" "ecs" {
  name        = "${var.project_name}-ecs-sg"
  description = "Security group for ECS tasks"
  vpc_id      = data.aws_vpc.main.id

  ingress {
    description     = "Allow ALB to ECS"
    from_port       = var.litellm_port
    to_port         = var.litellm_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-ecs-sg"
    Project     = var.project_name
    Environment = var.env
  }
}


# =============================================================================
# Application Load Balancer
# =============================================================================
resource "aws_lb" "litellm" {
  name               = "${var.project_name}-alb"
  load_balancer_type = "application"
  subnets            = local.public_subnet_ids
  security_groups    = [aws_security_group.alb.id]
  internal           = false

  drop_invalid_header_fields = true

  tags = {
    Name        = "${var.project_name}-alb"
    Project     = var.project_name
    Environment = var.env
  }
}

resource "aws_wafv2_web_acl_association" "alb" {
  resource_arn = aws_lb.litellm.arn
  web_acl_arn  = aws_wafv2_web_acl.litellm.arn
}

resource "aws_lb_target_group" "litellm" {
  name        = "${var.project_name}-tg"
  port        = var.litellm_port
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.main.id
  target_type = "ip"

  health_check {
    path                = "/health/liveliness"
    port                = tostring(var.litellm_port)
    protocol            = "HTTP"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 10
    interval            = 30
  }

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.litellm.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.self_signed.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.litellm.arn
  }
}

resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = aws_lb.litellm.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}


# =============================================================================
# ECS Cluster and Service
# =============================================================================
resource "aws_cloudwatch_log_group" "litellm" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 30

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}

resource "aws_ecs_cluster" "litellm" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}

resource "aws_iam_role" "ecs_task_execution" {
  name = "${var.project_name}-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_secrets_access" {
  name = "${var.project_name}-secrets-access"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "secretsmanager:GetSecretValue"
      ]
      Resource = [
        aws_secretsmanager_secret.litellm_master_salt.arn,
        aws_secretsmanager_secret.litellm_db_url.arn,
        aws_secretsmanager_secret.phoenix_api_key.arn
      ]
    }]
  })
}

resource "aws_iam_role" "ecs_task" {
  name = "${var.project_name}-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}

resource "aws_iam_role_policy" "ecs_bedrock_access" {
  name = "${var.project_name}-bedrock-access"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock:ApplyGuardrail"
        ]
        Resource = "*"
      }
    ]
  })
}


resource "aws_ecs_task_definition" "litellm" {
  family                   = "${var.project_name}-task"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 1024
  memory                   = 2048
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([
    {
      name      = "litellm"
      image     = "${aws_ecr_repository.litellm.repository_url}:latest"
      essential = true

      environment = [
        { name = "AWS_REGION", value = data.aws_region.current.name },
        { name = "LITELLM_LOG", value = var.litellm_log_level },
        { name = "REDIS_HOST", value = module.elasticache.replication_group_primary_endpoint_address },
        { name = "REDIS_PORT", value = tostring(var.redis_port) },
        { name = "REDIS_PASSWORD", value = random_password.redis_password.result },
        { name = "REDIS_SSL", value = "True" },
        { name = "GUARDRAIL_ID", value = aws_bedrock_guardrail.content_filter.guardrail_id },
        { name = "GUARDRAIL_VERSION", value = aws_bedrock_guardrail_version.content_filter.version },
        { name = "AWS_ROLE_ARN", value = aws_iam_role.ecs_task.arn },
        { name = "PHOENIX_PROJECT_NAME", value = var.phoenix_project_name },
        { name = "PHOENIX_COLLECTOR_ENDPOINT", value = var.phoenix_collector_endpoint }
      ]

      secrets = [
        {
          name      = "LITELLM_MASTER_KEY"
          valueFrom = "${aws_secretsmanager_secret.litellm_master_salt.arn}:LITELLM_MASTER_KEY::"
        },
        {
          name      = "LITELLM_SALT_KEY"
          valueFrom = "${aws_secretsmanager_secret.litellm_master_salt.arn}:LITELLM_SALT_KEY::"
        },
        {
          name      = "UI_PASSWORD"
          valueFrom = "${aws_secretsmanager_secret.litellm_master_salt.arn}:LITELLM_MASTER_KEY::"
        },
        {
          name      = "DATABASE_URL"
          valueFrom = aws_secretsmanager_secret.litellm_db_url.arn
        },
        {
          name      = "PHOENIX_AP_KEY"
          valueFrom = aws_secretsmanager_secret.phoenix_api_key.arn
        }
      ]

      portMappings = [{
        containerPort = var.litellm_port
        hostPort      = var.litellm_port
        protocol      = "tcp"
      }]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.litellm.name
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}

resource "aws_ecs_service" "litellm" {
  name            = "${var.project_name}-service"
  cluster         = aws_ecs_cluster.litellm.id
  task_definition = aws_ecs_task_definition.litellm.arn
  desired_count   = var.desired_count
  launch_type     = var.launch_type

  # Force new deployment when image is rebuilt
  force_new_deployment = true

  network_configuration {
    subnets          = local.public_subnet_ids
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.litellm.arn
    container_name   = "litellm"
    container_port   = var.litellm_port
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  # Ensure new image is pushed before service update
  depends_on = [null_resource.docker_build_push]

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}
