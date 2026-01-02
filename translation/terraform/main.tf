
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


# S3 bucket encryption with KMS
resource "aws_s3_bucket_server_side_encryption_configuration" "logs_bucket_encryption" {
  bucket = var.buckets.logs

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.s3_snowflake_key.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

module "route_53_records" {
  source           = ""
  hosted_zone_name = var.hosted_zone_name
  subdomain        = var.subdomain
  alias_name       = module.load_balancer_with_ip_target.dns
  alias_zone_id    = module.load_balancer_with_ip_target.zone_id
}


module "lambda" {
  source                   = ""
  lambda_timeout           = var.lambda_timeout
  vpc_id                   = data.aws_vpc.main.id
  subnet_ids               = local.az_subnet_ids.workload
  enable_layers            = var.enable_layers
  create_custom_vpc_policy = var.create_custom_vpc_policy
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
  source                           = ""
  vpc_id                           = data.aws_vpc.main.id
  vpc_endpoint_security_group_id   = data.aws_security_group.endpoint_security_group.id
  endpoint_subnet_ids              = local.az_subnet_ids.endpoint
  tag                              = var.tag
  create_bedrock_vpc_endpoint      = var.create_bedrock_vpc_endpoint
  existing_bedrock_vpc_endpoint_id = var.existing_bedrock_vpc_endpoint_id
}


module "load_balancer_with_ip_target" {
  source                = ""
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
  count            = length(module.api_gateway.endpoint_private_ips) >= 1 ? 1 : 0
  target_group_arn = module.load_balancer_with_ip_target.target_group_arn
  target_id        = module.api_gateway.endpoint_private_ips[0]
  port             = var.target_group_port
}


resource "aws_lb_target_group_attachment" "attachment_2" {
  count            = length(module.api_gateway.endpoint_private_ips) >= 2 ? 1 : 0
  target_group_arn = module.load_balancer_with_ip_target.target_group_arn
  target_id        = module.api_gateway.endpoint_private_ips[1]
  port             = var.target_group_port
}


resource "aws_lb_target_group_attachment" "attachment_3" {
  count            = length(module.api_gateway.endpoint_private_ips) >= 3 ? 1 : 0
  target_group_arn = module.load_balancer_with_ip_target.target_group_arn
  target_id        = module.api_gateway.endpoint_private_ips[2]
  port             = var.target_group_port
}



module "acm_cert" {
  source                    = ""
  certificate_authority_arn = var.certificate_authority_arn
  domain_name               = module.route_53_records.record_fqdn
}


module "api_gateway" {
  source                         = ""
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
  create_vpc_endpoint            = var.create_vpc_endpoint
  external_vpc_endpoint_ids      = var.external_vpc_endpoint_ids
}


module "s3_logs" {
  source            = ""
  bucket_name       = var.buckets.logs
  expiration_days   = 180
  enable_expiration = true
  force_destroy     = true
}


module "s3_trust_store" {
  source      = ""
  bucket_name = var.buckets.trust_store
}


module "s3_python_packages" {
  source      = ""
  bucket_name = var.buckets.layers
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
