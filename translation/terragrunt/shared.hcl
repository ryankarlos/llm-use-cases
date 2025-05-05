locals {
  region    = "eu-west-1"
  product   = "redword-flagger"
  org       = "entain"
  channel   = "dsai"
  team      = "dsai"
  state_resource_name = join("-", [
    "${lower(local.org)}tfstate",
    get_aws_account_id()
  ])
}


# Configure the remote state backend
remote_state {
  backend = "s3"
  config = {
    bucket         = local.state_resource_name
    key            = "${local.org}/infrastructure/${local.product}.tfstate"
    region         = local.region
    encrypt        = true
    dynamodb_table = local.state_resource_name
  }
}

inputs = {
  team    = local.team
  region  = local.region
  product = local.product
  python_version_lambda = "python3.11"
  trust_store_name = "redword-truststore"
  lambda_role = "redword-flagger-role"
  subdomain = "redword"
  enable_layers = true
  tag = {name="redword"}
  http_method ="POST"
  alb_name = "redword-lb"
  api_gateway_model = "model"
}
