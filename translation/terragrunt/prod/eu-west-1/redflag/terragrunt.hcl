terraform {
   source = "${get_parent_terragrunt_dir()}/../terraform/products/redflag"
}

include {
  path = find_in_parent_folders("shared.hcl")

}

locals {
  env       = "prod"
  account_id = get_aws_account_id()
  common_vars = read_terragrunt_config(find_in_parent_folders("shared.hcl"))
}


inputs = {
  env     = local.env
  hosted_zone_name = "dsai-redword-flagger-${local.env}.aws.local"
  lambda_layers          = [
    "arn:aws:lambda:${local.common_vars.inputs.region}:${local.account_id}:layer:datetime-layer:1",
    "arn:aws:lambda:${local.common_vars.inputs.region}:${local.account_id}:layer:nltk-data:1",
    "arn:aws:lambda:${local.common_vars.inputs.region}:${local.account_id}:layer:nltk-layer-package:1",
    "arn:aws:lambda:${local.common_vars.inputs.region}:${local.account_id}:layer:regex-layer:2"
  ]
  stage_name = local.env

  certificate_authority_arn = "arn:aws:acm-pca:${local.common_vars.inputs.region}:571600854145:certificate-authority/b3a41930-2d19-4a1f-8172-2213e1a9ba60"
  buckets = {logs="redword-logs-${local.env}", layers="redword-python-packages-${local.env}", trust_store=local.common_vars.inputs.trust_store_name}
  resource_path = "redwords-${local.env}"
  cert_local_file = "${get_env("CERT", "${get_parent_terragrunt_dir()}/../terraform/products/redflag/CertificateProd.pem")}"
}
