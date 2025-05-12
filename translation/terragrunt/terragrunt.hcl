terraform {
   source = "${get_parent_terragrunt_dir()}"
}


remote_state {
  backend = "local"
  generate = {
    path      = "backend.tf"
    if_exists = "overwrite"
  }
  config = {
    path = "${get_terragrunt_dir()}/terraform.tfstate"
  }
}

locals {
  account_id =  get_aws_account_id()
  region = "us-east-1"
}

inputs = {
  hosted_zone_name = "ryannaz-mlops.com"
  stage_name = "llm-translation-speech"
  resource_path = "llm-api"
  cert_local_file = "${get_parent_terragrunt_dir()}/../Certificate.pem"
  python_version_lambda = "python3.11"
  lambda_role = "redword-flagger-role"
  subdomain = "redword"
  enable_layers = false
  tag = {name="redword"}
  http_method ="POST"
  alb_name = "redword-lb"
  api_gateway_model = "model"
}
