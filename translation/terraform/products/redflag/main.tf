
locals {
  az_subnet_ids = {
    workload = flatten([
      for az, subnets in data.aws_subnets.workload_subnet : subnets.ids
    ])
    endpoint = flatten([
      for az, subnets in data.aws_subnets.endpoint_subnet : subnets.ids
    ])
  }


  lambda_layers_source_dir = "${path.module}/code/lambda/layers"
  lambda_code_source_dir   = "${path.module}/code/lambda/redflag_lambda_function"
  lambda_zip_output_path   = "${path.module}/code/lambda/lambda_function.zip"

  model_schema = jsonencode({
    "$schema" : "http://json-schema.org/draft-04/schema#",
    "title" : "CreateUserRequest",
    "type" : "object",
    "properties" : {
      "TicketId" : {
        "type" : "string"
      },
      "ConversationId" : {
        "type" : "string"
      },
      "TicketCreatedTime" : {
        "type" : "string"
      },
      "TranscriptEndTime" : {
        "type" : "string"
      },
      "Language" : {
        "type" : "string"
      },
      "Label" : {
        "type" : "string"
      },
      "CustomerName" : {
        "type" : "string"
      },
      "CustomerCountry" : {
        "type" : ["string", "null"]
      },
      "BotName" : {
        "type" : "string"
      },
      "AgentName" : {
        "type" : "string"
      },
      "AgentTeamName" : {
        "type" : ["string", "null"]
      },
      "CustomerPriorityLevel" : {
        "type" : "string"
      },
      "TranscriptAuthorName" : {
        "type" : "string"
      },
      "IncrementalTranscript" : {
        "type" : "string"
      },
      "Category" : {
        "type" : "string"
      },
      "OutboundCategory" : {
        "type" : "string"
      },
      "Channel" : {
        "type" : "string"
      },
      "LoginStatus" : {
        "type" : "string"
      },
      "RegisteredContact" : {
        "type" : ["string", "null"]
      },
      "CustomerEmailID" : {
        "type" : ["string", "null"]
      },
      "RecievedAtEmailId" : {
        "type" : ["string", "null"]
      },
      "Subject" : {
        "type" : "string"
      },
      "AccountId" : {
        "type" : "string"
      },
      "LabelPrefix" : {
        "type" : "string"
      }
    },
    "required" : ["TicketId", "ConversationId", "TicketCreatedTime", "CustomerName", "AgentName", "Language", "IncrementalTranscript", "Channel"]
  })

}


module "route_53_records" {
  source           = "git::https://vie.git.bwinparty.com/marketing-data-science/terraform/modules.git//route_53/alias_record"
  hosted_zone_name = var.hosted_zone_name
  subdomain        = var.subdomain
  alias_name       = module.load_balancer_with_ip_target.dns
  alias_zone_id    = module.load_balancer_with_ip_target.zone_id
}


module "lambda" {
  source         = "git::https://vie.git.bwinparty.com/marketing-data-science/terraform/modules.git//lambda/zip"
  lambda_timeout = var.lambda_timeout
  vpc_id         = data.aws_vpc.main.id
  subnet_ids     = local.az_subnet_ids.workload
  enable_layers  = var.enable_layers
  lambda_layers = [
    aws_lambda_layer_version.lambda_layer_nltk_layer.arn,
    aws_lambda_layer_version.lambda_layer_datetime.arn,
    aws_lambda_layer_version.lambda_layer_nltk_s3.arn,
    aws_lambda_layer_version.lambda_layer_regex_layer.arn
  ]
  security_group_id = data.aws_security_group.workload_security_group.id
  function_name     = var.lambda_function_name
  lambda_role       = var.lambda_role
  environment_variables = {
    "S3_LOGS_BUCKET" = "${var.buckets.logs}"
  }
  filename         = local.lambda_zip_output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256 # filebase64sha256(var.lambda_zip_output_path)
  depends_on       = [data.archive_file.lambda_zip]
}


module "bedrock_endpoint" {
  source                         = "git::https://vie.git.bwinparty.com/marketing-data-science/terraform/modules.git//bedrock"
  vpc_id                         = data.aws_vpc.main.id
  vpc_endpoint_security_group_id = data.aws_security_group.endpoint_security_group.id
  endpoint_subnet_ids            = local.az_subnet_ids.endpoint
  tag                            = var.tag
}


module "load_balancer_with_ip_target" {
  source                = "git::https://vie.git.bwinparty.com/marketing-data-science/terraform/modules.git//load_balancer/application/ip_target"
  vpc_id                = data.aws_vpc.main.id
  subnet_ids            = local.az_subnet_ids.workload
  certificate_arn       = module.acm_cert.certificate_arn
  tag                   = var.tag
  security_group_id     = data.aws_security_group.workload_security_group.id
  trust_store_name      = var.trust_store_name
  trust_store_bucket    = module.s3_trust_store.s3_bucket_id
  cert_s3_key           = aws_s3_object.cert_chain.id
  alb_name              = var.alb_name
  target_group_port     = var.target_group_port
  target_group_protocol = var.target_group_protocol
  health_check_protocol = var.health_check_protocol
}


resource "aws_lb_target_group_attachment" "attachment_1" {
  target_group_arn = module.load_balancer_with_ip_target.target_group_arn
  target_id        = module.api_gateway.endpoint_private_ips[0]
  port             = var.target_group_port
}


resource "aws_lb_target_group_attachment" "attachment_2" {
  target_group_arn = module.load_balancer_with_ip_target.target_group_arn
  target_id        = module.api_gateway.endpoint_private_ips[1]
  port             = var.target_group_port
}


resource "aws_lb_target_group_attachment" "attachment_3" {
  target_group_arn = module.load_balancer_with_ip_target.target_group_arn
  target_id        = module.api_gateway.endpoint_private_ips[2]
  port             = var.target_group_port
}



module "acm_cert" {
  source                    = "git::https://vie.git.bwinparty.com/marketing-data-science/terraform/modules.git//acm_certificate"
  certificate_authority_arn = var.certificate_authority_arn
  domain_name               = module.route_53_records.record_fqdn
}


module "api_gateway" {
  source                         = "git::https://vie.git.bwinparty.com/marketing-data-science/terraform/modules.git//api_gateway"
  stage_name                     = var.stage_name
  domain_name                    = module.route_53_records.record_fqdn
  certificate_arn                = module.acm_cert.certificate_arn
  lambda_function_invoke_arn     = module.lambda.invoke_arn
  lambda_function_name           = var.lambda_function_name
  vpc_id                         = data.aws_vpc.main.id
  endpoint_subnet_ids            = local.az_subnet_ids.endpoint
  vpc_endpoint_security_group_id = data.aws_security_group.workload_security_group.id
  tag                            = var.tag
  integration_timeout            = var.integration_timeout
  resource_path                  = var.resource_path
  http_method                    = var.http_method
  model_schema                   = local.model_schema
}


module "s3_logs" {
  source            = "git::https://vie.git.bwinparty.com/marketing-data-science/terraform/modules.git//s3"
  bucket_name       = var.buckets.logs
  expiration_days   = 180
  enable_expiration = true
  force_destroy     = true
}


module "s3_trust_store" {
  source      = "git::https://vie.git.bwinparty.com/marketing-data-science/terraform/modules.git//s3"
  bucket_name = var.buckets.trust_store
}


module "s3_python_packages" {
  source      = "git::https://vie.git.bwinparty.com/marketing-data-science/terraform/modules.git//s3"
  bucket_name = var.buckets.layers
}



resource "aws_iam_role_policy_attachment" "lambda_bedrock" {
  role       = var.lambda_role
  policy_arn = "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
  depends_on = [module.lambda]
}


resource "aws_iam_role_policy_attachment" "lambda_translate" {
  role       = var.lambda_role
  policy_arn = "arn:aws:iam::aws:policy/TranslateFullAccess"
  depends_on = [module.lambda]
}


resource "aws_lambda_layer_version" "lambda_layer_nltk_layer" {
  layer_name          = "nltk_layer"
  compatible_runtimes = ["python3.11"]
  filename            = "${local.lambda_layers_source_dir}/nltk-layer.zip"

  source_code_hash = filebase64sha256("${local.lambda_layers_source_dir}/nltk-layer.zip")
  lifecycle {
    ignore_changes = [filename]
  }
}


resource "aws_lambda_layer_version" "lambda_layer_datetime" {
  layer_name          = "datetime"
  compatible_runtimes = [var.python_version_lambda]
  filename            = "${local.lambda_layers_source_dir}/datetime.zip"

  source_code_hash = filebase64sha256("${local.lambda_layers_source_dir}/datetime.zip")
  lifecycle {
    ignore_changes = [filename] # add this to avoid drift due to different paths in ci-cd and local
  }
}


resource "aws_lambda_layer_version" "lambda_layer_regex_layer" {
  layer_name          = "regex_layer"
  compatible_runtimes = [var.python_version_lambda]
  filename            = "${local.lambda_layers_source_dir}/regex-layer.zip"

  source_code_hash = filebase64sha256("${local.lambda_layers_source_dir}/regex-layer.zip")
  lifecycle {
    ignore_changes = [filename] # add this to avoid drift due to different paths in ci-cd and local
  }
}

# Uploading layers to S3
resource "aws_s3_object" "nltk_data_layer" {
  bucket = module.s3_python_packages.s3_bucket_id
  key    = "nltk-data.zip"
  source = "${local.lambda_layers_source_dir}/nltk-data.zip"
  lifecycle {
    ignore_changes = [source] # add this to avoid drift due to different paths in ci-cd and local
  }
}



resource "aws_lambda_layer_version" "lambda_layer_nltk_s3" {
  layer_name          = "nltk_data"
  compatible_runtimes = [var.python_version_lambda]
  s3_bucket           = module.s3_python_packages.s3_bucket_id
  s3_key              = aws_s3_object.nltk_data_layer.key
}



resource "aws_vpc_security_group_ingress_rule" "http" {
  security_group_id = data.aws_security_group.workload_security_group.id
  description       = "allow http inbound traffic from vpc cidr range"
  cidr_ipv4         = "10.0.0.0/8"
  from_port         = 80
  ip_protocol       = "tcp"
  to_port           = 80
}



resource "aws_vpc_security_group_ingress_rule" "https" {
  security_group_id = data.aws_security_group.workload_security_group.id
  description       = "allow https inbound traffic from vpc cidr range"
  #cidr_ipv4         = data.aws_vpc.main.cidr_block
  cidr_ipv4   = "10.0.0.0/8" # replace with entain cidr range
  from_port   = 443
  ip_protocol = "tcp"
  to_port     = 443
}

resource "time_sleep" "wait_time" {
  depends_on = [module.acm_cert]

  create_duration = "30s"
}


resource "aws_s3_object" "cert_chain" {
  bucket = module.s3_trust_store.s3_bucket_id
  key    = "cert.pem"
  source = var.cert_local_file
  lifecycle {
    ignore_changes = [source] # add this to avoid drift due to different paths in ci-cd and local
  }
}

resource "null_resource" "lambda_zip_trigger" {
  triggers = {
    trigger = timestamp()
  }
}


data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = local.lambda_code_source_dir
  output_path = local.lambda_zip_output_path
  depends_on  = [null_resource.lambda_zip_trigger]
}
