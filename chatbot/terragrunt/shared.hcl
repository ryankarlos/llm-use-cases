locals {
  region    = "eu-west-1"
  product   = "prometheus"
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
  mtls_trust_store_name = "prometheus-truststore"
  subdomain = "prometheus"
  tag = {name="prometheus"}
  alb_name = "prometheus-lb"
  cluster_name = "prometheus-cluster"
  service_name = "prometheus-service"
  container_name = "prometheus-container"
  launch_type = "FARGATE"
  min_capacity = 2
  max_capacity = 4
  desired_count = 2
  task_execution_role_name = "PrometheusTaskExecutionRole"
  task_role_name = "PrometheusTaskRole"
}
