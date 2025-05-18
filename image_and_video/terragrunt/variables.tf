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

variable "security_group_id" {
  description = "security_group_id"
  type        = string
}

variable "subnet_ids" {
  description = "subnet_ids"
  type        = list(string)
}

variable "vpc_id" {
  description = "vpc_id"
  type        = string
}

# Add new variables for Cognito user
variable "cognito_username" {
  description = "Username for Cognito user"
  type        = string
}

variable "cognito_email" {
  description = "Email for Cognito user"
  type        = string
}

variable "cognito_generate_password" {
  description = "Whether to generate a password for the Cognito user"
  type        = bool
  default     = true
}

variable "cognito_send_email" {
  description = "Whether to send an email to the Cognito user"
  type        = bool
  default     = true
}