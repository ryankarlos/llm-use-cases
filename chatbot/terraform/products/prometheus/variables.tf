
variable "env" {
  description = "account environment e.g. dev or prod"
  type        = string
}

variable "image_uri" {
  description = "docker image uri for ECS"
  type        = string
}

variable "cluster_name" {
  description = "Name of the ECS cluster"
  type        = string
}

variable "service_name" {
  description = "Name of the ECS service"
  type        = string
}

variable "container_name" {
  description = "Name of the container"
  type        = string
}



variable "alb_name" {
  description = "Name of the application load balancer"
  type        = string
}


variable "region" {
  description = "aws region"
  type        = string
}


variable "max_capacity" {
  description = "Maximum number of tasks"
  type        = number
}

variable "min_capacity" {
  description = "Minimum number of tasks"
  type        = number
}

variable "desired_count" {
  description = "Desired number of tasks"
  type        = number
}


variable "launch_type" {
  description = "Launch type for the ECS service (FARGATE or EC2)"
  type        = string
}

variable "hosted_zone_name" {
  description = "route53 private hosted zone name"
  type        = string
}


variable "subdomain" {
  description = "subdomain for route53 record"
  type        = string
}

variable "certificate_authority_arn" {
  description = "private CA arn"
  type        = string
}


variable "tag" {
  description = "tag object"
  type = object({
    name = string
  })
}


variable "task_execution_role_name" {
  description = "Task execution role name"
  type        = string
}


variable "task_role_name" {
  description = "Task role name"
  type        = string
}

variable "container_port" {
  description = "ecs container port"
  type        = number
  default     = 8501
}


variable "host_port" {
  description = "ecs host port"
  type        = number
  default     = 8501
}


variable "bucket_name" {
  type        = string
  description = "Name of the S3 bucket"
}


variable "target_group_name" {
  description = "target group name"
  type        = string
}

variable "cognito_user_pool_name" {
  description = "name of cognito user pool"
  type        = string
  default     = "prometheus_cognito_pool"
}

variable "cognito_users" {
  description = "map of cognito usernames and emails"
  type        = map(string)
  default     = {}
}
