



module "route_53_records" {
  source           = "github.com/ryankarlos/terraform_modules.git//aws/route_53/alias_record"
  hosted_zone_name = var.hosted_zone_name
  subdomain        = var.subdomain
  alias_name       = module.load_balancer.dns
  alias_zone_id    = module.load_balancer.zone_id
}




module "load_balancer" {
  source                       = "github.com/ryankarlos/terraform_modules.git//aws/load_balancer/application/ip_target"
  vpc_id                       = var.vpc_id
  subnet_ids                   = var.subnet_ids
  certificate_arn              = aws_acm_certificate.cert.arn
  security_group_id            = var.security_group_id
  alb_name                     = var.alb_name
  tag                          = var.tag
  target_group_port            = var.host_port
  health_check_path            = "/status"
}


module "ecs" {
  source = "github.com/ryankarlos/terraform_modules.git//aws/ecs"

  cluster_name                    = var.cluster_name
  service_name                    = var.service_name
  container_name                  = var.container_name
  subnet_ids                      = var.subnet_ids
  desired_count                   = var.desired_count
  min_capacity                    = var.min_capacity
  max_capacity                    = var.max_capacity
  launch_type                     = var.launch_type
  security_group_ids              = [var.security_group_id]
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
        },
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
  schema {
    name                     = "group"
    attribute_data_type      = "String"
    developer_only_attribute = false
    mutable                  = true 
    required                 = false 
    string_attribute_constraints {}
  }
}


resource "aws_cognito_user_pool_client" "client" {
  name                         = "client"
  generate_secret              = true
  user_pool_id                 = aws_cognito_user_pool.user_pool.id
  callback_urls                = ["https://${var.subdomain}/${var.hosted_zone_name}/oauth2/idpresponse"]
  logout_urls                  = ["https://${var.subdomain}/${var.hosted_zone_name}"]
  allowed_oauth_flows          = ["code"]
  allowed_oauth_scopes         = ["email", "openid", "profile"]
  allowed_oauth_flows_user_pool_client = true
  supported_identity_providers = ["COGNITO"]
   token_validity_units {
      access_token  = "minutes" 
      id_token      = "minutes" 
      refresh_token = "days" 
  }
}

# Add Cognito user
resource "aws_cognito_user" "user" {
  user_pool_id = aws_cognito_user_pool.user_pool.id
  username     = var.cognito_username
  
  attributes = {
    email          = var.cognito_email
    email_verified = true
  }

}

resource "awscc_bedrock_guardrail" "example" {
  name                      = "example_guardrail"
  blocked_input_messaging   = "Blocked input"
  blocked_outputs_messaging = "Blocked output"
  description               = "Example guardrail"

  content_policy_config = {
    filters_config = [
      {
        input_strength  = "MEDIUM"
        output_strength = "MEDIUM"
        type            = "HATE"
      },
      {
        input_strength  = "HIGH"
        output_strength = "HIGH"
        type            = "VIOLENCE"
      }
    ]
  }

  tags = [{
    key   = "Modified By"
    value = "AWSCC"
  }]

}


resource "aws_acm_certificate" "cert" {
  domain_name       = "${var.subdomain}.${var.hosted_zone_name}"
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}


resource "aws_route53_record" "example" {
  for_each = {
    for dvo in aws_acm_certificate.cert.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.selected.zone_id
}


resource "aws_ecr_repository" "foo" {
  name                 = var.ecr_repo_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}