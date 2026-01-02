
variable "create" {
  description = "whether to create resource or not"
  type        = bool
  default     = true
}


variable "lambda_memory" {
  description = "lambda memory"
  type        = number
  default     = 2048
}



variable "lambda_timeout" {
  description = "timeout for lambda function in seconds"
  type        = number
  default     = 600
}


variable "integration_timeout" {
  description = "integration timeout in milliseconds"
  type        = number
  default     = 120000
}


variable "hosted_zone_name" {
  description = "route53 private hosted zone name"
  type        = string
}


variable "subdomain" {
  description = "subdomain for route53 record"
  type        = string
}


variable "tag" {
  description = "tag object"
  type = object({
    name = string
  })
}


variable "trust_store_name" {
  description = "trust store name"
  type        = string
}


variable "lambda_function_name" {
  description = "name of lambda function"
  type        = string
}


variable "enable_layers" {
  description = "Boolean flag to enable/disable Lambda layers"
  type        = bool
}

variable "lambda_layers" {
  description = "List of Lambda layer ARNs to attach"
  type        = list(string)
}

variable "certificate_authority_arn" {
  description = "private CA arn"
  type        = string
}

variable "stage_name" {
  description = "api gateway stage name"
  type        = string
}

variable "buckets" {
  description = "api gateway stage name"
  type = object({
    logs        = string
    layers      = string
    trust_store = string
  })
}



variable "resource_path" {
  description = "api gateway resource path"
  type        = string
}

variable "lambda_role" {
  description = "lambda role name"
  type        = string
}

variable "http_method" {
  description = "method for api gateway e.g. GET, POST"
  type        = string
}

variable "api_gateway_model" {
  description = "method for api gateway e.g. GET, POST"
  type        = string
}


variable "python_version_lambda" {
  description = "python compatibe runtime for python packages"
  type        = string
}

variable "alb_name" {
  description = "name of load balancer"
  type        = string
}


variable "cert_local_file" {
  description = "path to passphrase file"
  type        = string
}



variable "target_group_port" {
  description = "target group port"
  type        = number
  default     = 443
}


variable "target_group_protocol" {
  description = "target group protocol"
  type        = string
  default     = "HTTPS"
}

# needs to be same as target group protocol (https) if listener us https
# or observe unhealthy target
variable "health_check_protocol" {
  description = "target group protocol"
  type        = string
  default     = "HTTPS"
}

variable "external_vpc_endpoint_ids" {
  type        = list(string)
  default     = []
  description = "External VPC endpoint IDs to use when not creating internally"
}


variable "create_vpc_endpoint" {
  description = "Whether to create the VPC endpoint"
  type        = bool
  default     = true
}

variable "create_bedrock_vpc_endpoint" {
  type    = bool
  default = true
}

variable "existing_bedrock_vpc_endpoint_id" {
  type    = list(string)
  default = [] # required only if not creating new
}

variable "create_custom_vpc_policy" {
  type    = bool
  default = true
}

variable "create_dashboard" {
  description = "Whether to create CloudWatch dashboard"
  type        = bool
}

variable "dashboard_name" {
  description = "Name of the CloudWatch dashboard"
  type        = string
}
