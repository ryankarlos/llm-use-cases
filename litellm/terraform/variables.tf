
variable "project_name" {
  description = "Project name for tagging resources"
  type        = string
  default     = "myproject"
}

variable "image_uri_litellm" {
  description = "docker image uri litellm for ECS"
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


variable "litellm_secret_name" {
  description = "litellm secret name"
  type        = string
}


variable "litellm_secret_values" {
  description = "litellm secret values"
  type        = string
  sensitive   = true
}


variable "litellm_dir" {
  description = "litellm_config_dir"
  type        = string
}


variable "litellm_config_name" {
  description = "litellm config file name"
  type        = string
  default     = "config.yaml"
}


variable "litellm_log_level" {
  type        = string
  description = "litellm log level"
  default     = "DEBUG"
}


variable "engine_version" {
  description = "Version number of the cache engine to be used. Defaults to `7.2`"
  type        = string
  default     = "7.2"
}

variable "node_type" {
  description = "The instance class used. Defaults to `cache.t4g.small`"
  type        = string
  default     = "cache.t4g.small"
}

variable "cluster_mode" {
  description = "Specifies whether cluster mode is enabled or disabled."
  type        = string
  default     = null

  validation {
    condition     = var.cluster_mode == null ? true : contains(["enabled", "disabled", "compatible"], var.cluster_mode)
    error_message = "The cluster mode must be null or one of: enabled, disabled, compatible"
  }
}

variable "cluster_mode_enabled" {
  description = "Whether to enable Redis [cluster mode https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/Replication.Redis-RedisCluster.html]"
  type        = bool
  default     = false
}

variable "apply_immediately" {
  description = "Whether any database modifications are applied immediately, or during the next maintenance window. Defaults to `false`"
  type        = bool
  default     = false
}

variable "maintenance_window" {
  description = "Specifies the weekly time range for when maintenance on the cache cluster is performed. The format is `ddd:hh24:mi-ddd:hh24:mi` (24H Clock UTC). Defaults to Sunday 5AM-9AM"
  type        = string
  default     = "sun:05:00-sun:09:00"
}

variable "subnet_group_name" {
  description = "The name of the replication group"
  type        = string
  default     = null
}

variable "create_parameter_group" {
  description = "Determines whether the ElastiCache parameter group will be created or not. Defaults to `true`"
  type        = bool
  default     = true
}

variable "parameter_group_name" {
  description = "The name of the parameter group. If `create_parameter_group` is `true`, this is the name assigned to the parameter group created. Otherwise, this is the name of an existing parameter group"
  type        = string
  default     = null
}

variable "parameter_group_family" {
  description = "Family of the ElastiCache parameter group"
  type        = string
  default     = "valkey7"
}

variable "create_replication_group" {
  description = "Determines whether an ElastiCache replication group will be created or not. Defaults to `true`"
  type        = bool
  default     = true
}


variable "replication_group_id" {
  description = "Replication group identifier. When `create_replication_group` is set to `true`, this is the ID assigned to the replication group created. When `create_replication_group` is set to `false`, this is the ID of an externally created replication group"
  type        = string
  default     = null
}



variable "transit_encryption_enabled" {
  description = "Determines whether encryption in-transit is enabled"
  type        = bool
  default     = true
}

variable "parameter_list" {
  description = "List of ElastiCache parameters to apply"
  type = list(object({
    name  = string
    value = string
  }))
}




variable "multi_az_enabled" {
  description = "Determines whether or not Multi AZ support is enabled for the Replication Group. Defaults to `true`"
  type        = bool
  default     = true
}

variable "num_node_groups" {
  description = "Number of node groups (shards) for this Redis replication group. Changing this number will trigger a resizing operation before other settings modifications. Conflicts with `num_cache_clusters`."
  type        = number
  default     = 1
}

variable "replicas_per_node_group" {
  description = "Number of replica nodes in each node group. Changing this number will trigger a resizing operation before other settings modifications. Conflicts with num_cache_clusters. Can only be set if num_node_groups is set."
  type        = number
  default     = null

  validation {
    condition     = var.replicas_per_node_group == null ? true : var.replicas_per_node_group >= 0 && var.replicas_per_node_group <= 5
    error_message = "Replicas per node group must be between 0 and 5"
  }
}

variable "num_cache_clusters" {
  description = "Number of cache clusters (primary and replicas) this replication group will have. Only applicable if `multi_az_enabled` is set to `true`. Conflicts with num_node_groups and replicas_per_node_group. "
  type        = number
  default     = 2
  validation {
    condition     = var.num_cache_clusters >= 2
    error_message = "The number of cache clusters cannot be lower than 2"
  }
}

variable "automatic_failover_enabled" {
  description = "Specifies whether a read-only replica will be automatically promoted to read/write primary if the existing primary fails. If true, Multi-AZ is enabled for this replication group"
  type        = bool
  default     = true
}


variable "create_monitoring_role" {
  type        = bool
  description = "Determines whether to create the IAM role for RDS enhanced monitoring"
  default     = true
}

variable "monitoring_interval" {
  type        = number
  default     = 0
  description = "Monitoring interval (seconds); 0 disables Enhanced Monitoring"
  validation {
    condition     = var.monitoring_interval == 0 || contains([1, 5, 10, 15, 30, 60], var.monitoring_interval)
    error_message = "Monitoring interval must be 0 or one of [1, 5, 10, 15, 30, 60]."
  }
}

variable "performance_insights_enabled" {
  description = "Enable Performance Insights"
  type        = bool
  default     = true
}

variable "performance_insights_kms_key_id" {
  description = "KMS key for Performance Insights encryption. Defaults to 'alias/rds' key."
  type        = string
  default     = null
}



variable "skip_final_snapshot" {
  description = "If true, final snapshot will be skipped"
  default     = false
  type        = bool
}

variable "final_snapshot_identifier" {
  description = "Custom identifier for final DB snapshot. If null, one will be auto-generated."
  type        = string
  default     = null
}


variable "ingress_cidr_range" {
  description = "ingress cidr range for DBs"
  type        = string
  default     = "10.0.0.0/8"
}


variable "aurora_scaling_config" {
  description = "Scaling configuration for Aurora Serverless v2"
  type = object({
    min_capacity = number
    max_capacity = number
  })
  default = {
    min_capacity = 2
    max_capacity = 16
  }
}

