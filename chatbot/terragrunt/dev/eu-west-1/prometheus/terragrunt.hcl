terraform {
   source = "${get_parent_terragrunt_dir()}/../terraform/products/prometheus"
}

include {
  path = find_in_parent_folders("shared.hcl")

}

locals {
  env       = "dev"
  account_id =  get_aws_account_id()
  common_vars = read_terragrunt_config(find_in_parent_folders("shared.hcl"))
}

inputs = {
  env     = local.env
  hosted_zone_name = "data-science-${local.env}.aws.local"
  image_uri = "${local.account_id}.dkr.ecr.${local.common_vars.inputs.region}.amazonaws.com/${get_env("ECR_REPO","dsai/prometheus:latest")}"
  certificate_authority_arn = "arn:aws:acm-pca:${local.common_vars.inputs.region}:160885259864:certificate-authority/1cbe4fcf-15e3-4f2b-a72f-cd88c6834c32"
  env         = "dev"
  bucket_name = "prometheus-bucket"
  target_group_name = "prometheus-lb-target"
  cognito_users = {
    "ryan": "ryan.nazareth@entaingroup.com"
  }
}
