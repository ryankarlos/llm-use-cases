
locals {
  az_subnet_ids = {
    workload = flatten([
      for az, subnets in data.aws_subnets.workload_subnet : subnets.ids
    ])
    endpoint = flatten([
      for az, subnets in data.aws_subnets.endpoint_subnet : subnets.ids
    ])
  }
}

module "route_53_records" {
  source           = "git::https://vie.git.bwinparty.com/marketing-data-science/terraform/modules.git//route_53/alias_record"
  hosted_zone_name = var.hosted_zone_name
  subdomain        = var.subdomain
  alias_name       = module.load_balancer.dns
  alias_zone_id    = module.load_balancer.zone_id
}

module "acm_cert" {
  source                    = "git::https://vie.git.bwinparty.com/marketing-data-science/terraform/modules.git//acm_certificate"
  certificate_authority_arn = var.certificate_authority_arn
  domain_name               = module.route_53_records.record_fqdn
}


module "load_balancer" {
  source                       = "git::https://vie.git.bwinparty.com/marketing-data-science/terraform/modules.git//load_balancer/application/ip_target"
  vpc_id                       = data.aws_vpc.main.id
  subnet_ids                   = local.az_subnet_ids.workload
  certificate_arn              = module.acm_cert.certificate_arn
  security_group_id            = data.aws_security_group.workload_security_group.id
  alb_name                     = var.alb_name
  tag                          = var.tag
  target_group_port            = var.host_port
  target_group_name            = var.target_group_name
  enable_mutual_authentication = false
  health_check_path            = "/status"
}


module "ecs" {
  source = "git::https://vie.git.bwinparty.com/marketing-data-science/terraform/modules.git//ecs"

  cluster_name                    = var.cluster_name
  service_name                    = var.cluster_name
  container_name                  = var.container_name
  subnet_ids                      = local.az_subnet_ids.workload
  desired_count                   = var.desired_count
  min_capacity                    = var.min_capacity
  max_capacity                    = var.max_capacity
  launch_type                     = var.launch_type
  security_group_ids              = [data.aws_security_group.workload_security_group.id]
  task_execution_role_name        = var.task_execution_role_name
  task_role_name                  = var.task_role_name
  enable_load_balancer            = true
  enable_circuit_breaker_rollback = true
  enable_circuit_breaker          = true

  container_definitions = jsonencode([
    {
      name      = var.container_name
      essential = true
      environment = [
        {
          name  = "ENV"
          value = var.env
        },
        {
          name  = "POOL_ID"
          value = aws_cognito_user_pool.user_pool.id
        },
        {
          name  = "APP_CLIENT_ID"
          value = aws_cognito_user_pool_client.client.id
        },
        {
          name  = "APP_CLIENT_SECRET"
          value = aws_cognito_user_pool_client.client.client_secret
        }
      ]
      image = var.image_uri
      portMappings = [{
        appProtocol   = "http"
        containerPort = var.container_port
        hostPort      = var.host_port
        name          = "${var.container_name}--80-tcp"
        protocol      = "tcp"
      }]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "${var.cluster_name}"
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "ecs"
          "awslogs-create-group"  = "true"
          "mode" : "non-blocking",
        }
      }
  }])
  scaling_type     = "step"
  container_port   = var.container_port
  target_group_arn = module.load_balancer.target_group_arn
}

module "bedrock_endpoint" {
  source                         = "git::https://vie.git.bwinparty.com/marketing-data-science/terraform/modules.git//bedrock"
  vpc_id                         = data.aws_vpc.main.id
  vpc_endpoint_security_group_id = data.aws_security_group.endpoint_security_group.id
  endpoint_subnet_ids            = local.az_subnet_ids.endpoint
  tag                            = { name : "bedrock-vpce" }
}


resource "aws_iam_role_policy_attachment" "bedrock_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
  role       = module.ecs.ecs_task_role_name
}

resource "aws_cognito_user_pool" "user_pool" {
  name = var.cognito_user_pool_name

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  password_policy {
    minimum_length    = 6
    require_lowercase = true
    require_numbers   = false
    require_symbols   = false
    require_uppercase = false
  }
}

resource "aws_cognito_user_pool_client" "client" {
  name            = "client"
  generate_secret = true
  user_pool_id    = aws_cognito_user_pool.user_pool.id
}
