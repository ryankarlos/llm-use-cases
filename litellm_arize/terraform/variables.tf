variable "project_name" {
  description = "Project name for tagging resources"
  type        = string
  default     = "litellm-demo"
}

variable "image_uri_litellm" {
  description = "Docker image URI for LiteLLM ECS"
  type        = string
}

variable "tag" {
  description = "Tag object"
  type = object({
    name = string
  })
  default = {
    name = "litellm-demo"
  }
}

variable "litellm_log_level" {
  description = "LiteLLM log level"
  type        = string
  default     = "DEBUG"
}

variable "env" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "litellm_port" {
  description = "Port for LiteLLM container"
  type        = number
  default     = 4000
}

variable "redis_port" {
  description = "Port for Redis/Valkey"
  type        = number
  default     = 6379
}


# =============================================================================
# ECS Configuration
# =============================================================================
variable "desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 1
}

variable "min_capacity" {
  description = "Minimum capacity for ECS auto scaling"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Maximum capacity for ECS auto scaling"
  type        = number
  default     = 4
}

variable "launch_type" {
  description = "ECS launch type"
  type        = string
  default     = "FARGATE"
}

# =============================================================================
# ElastiCache (Valkey) Configuration
# =============================================================================
variable "engine_version" {
  description = "Valkey engine version"
  type        = string
  default     = "7.2"
}

variable "node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t4g.small"
}

variable "cluster_mode" {
  description = "Cluster mode setting"
  type        = string
  default     = null
}

variable "cluster_mode_enabled" {
  description = "Enable cluster mode"
  type        = bool
  default     = false
}

variable "num_node_groups" {
  description = "Number of node groups"
  type        = number
  default     = 1
}

variable "replicas_per_node_group" {
  description = "Replicas per node group"
  type        = number
  default     = null
}

variable "multi_az_enabled" {
  description = "Enable Multi-AZ"
  type        = bool
  default     = true
}

variable "num_cache_clusters" {
  description = "Number of cache clusters"
  type        = number
  default     = 2
}

variable "automatic_failover_enabled" {
  description = "Enable automatic failover"
  type        = bool
  default     = true
}

variable "transit_encryption_enabled" {
  description = "Enable transit encryption"
  type        = bool
  default     = true
}

variable "apply_immediately" {
  description = "Apply changes immediately"
  type        = bool
  default     = false
}

variable "maintenance_window" {
  description = "Maintenance window"
  type        = string
  default     = "sun:05:00-sun:09:00"
}

variable "subnet_group_name" {
  description = "Subnet group name"
  type        = string
  default     = null
}

variable "create_parameter_group" {
  description = "Create parameter group"
  type        = bool
  default     = true
}

variable "parameter_group_name" {
  description = "Parameter group name"
  type        = string
  default     = null
}

variable "parameter_group_family" {
  description = "Parameter group family"
  type        = string
  default     = "valkey7"
}

variable "create_replication_group" {
  description = "Create replication group"
  type        = bool
  default     = true
}

variable "replication_group_id" {
  description = "Replication group ID"
  type        = string
  default     = null
}

variable "parameter_list" {
  description = "ElastiCache parameters"
  type = list(object({
    name  = string
    value = string
  }))
  default = [
    {
      name  = "maxmemory-policy"
      value = "volatile-lru"
    }
  ]
}


# =============================================================================
# Aurora PostgreSQL Configuration
# =============================================================================
variable "performance_insights_enabled" {
  description = "Enable Performance Insights"
  type        = bool
  default     = true
}

variable "performance_insights_kms_key_id" {
  description = "KMS key for Performance Insights"
  type        = string
  default     = null
}

variable "skip_final_snapshot" {
  description = "Skip final snapshot on deletion"
  type        = bool
  default     = true
}

variable "aurora_scaling_config" {
  description = "Aurora Serverless v2 scaling configuration"
  type = object({
    min_capacity = number
    max_capacity = number
  })
  default = {
    min_capacity = 0.5
    max_capacity = 4
  }
}

# =============================================================================
# Phoenix Cloud Configuration
# =============================================================================
variable "phoenix_api_key" {
  description = "Arize Phoenix cloud API key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "phoenix_project_name" {
  description = "Arize Phoenix project name"
  type        = string
  default     = "litellm-demo"
}

variable "phoenix_collector_endpoint" {
  description = "Arize Phoenix collector endpoint URL"
  type        = string
  default     = "https://app.phoenix.arize.com/v1/traces"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets (for Aurora/ElastiCache)"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access ALB (your IP address)"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "waf_whitelisted_ips" {
  description = "IP addresses to whitelist in WAF (CIDR format, e.g., 203.0.113.50/32)"
  type        = list(string)
  default     = []
}

variable "waf_rate_limit" {
  description = "Maximum requests per 5-minute period per IP before blocking (DDoS protection)"
  type        = number
  default     = 2000
}

variable "litellm_api_key" {
  description = "LiteLLM API key for external access (Lambda, etc.)"
  type        = string
  default     = ""
  sensitive   = true
}
