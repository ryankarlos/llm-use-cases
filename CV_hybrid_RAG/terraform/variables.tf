
variable "vector_dimension" {
  description = "The dimension of the vectors produced by the model."
  type        = number
  default     = 1024
}


variable "chunking_strategy" {
  type        = string
  description = "Chunking strategy to use (DEFAULT, FIXED_SIZE, HIERARCHICAL, SEMANTIC)"
  default     = "FIXED_SIZE"
  validation {
    condition     = contains(["DEFAULT", "FIXED_SIZE", "HIERARCHICAL", "SEMANTIC", "NONE"], var.chunking_strategy)
    error_message = "Chunking strategy must be one of: DEFAULT, FIXED_SIZE, HIERARCHICAL, SEMANTIC, NONE"
  }
}

# Fixed Size Chunking Variables
variable "fixed_size_max_tokens" {
  type        = number
  description = "Maximum number of tokens for fixed-size chunking"
  default     = 512
}

variable "fixed_size_overlap_percentage" {
  type        = number
  description = "Percentage of overlap between chunks"
  default     = 20
}

# Hierarchical Chunking Variables
variable "hierarchical_overlap_tokens" {
  type        = number
  description = "Number of tokens to overlap in hierarchical chunking"
  default     = 70
}

variable "hierarchical_parent_max_tokens" {
  type        = number
  description = "Maximum tokens for parent chunks"
  default     = 1000
}

variable "hierarchical_child_max_tokens" {
  type        = number
  description = "Maximum tokens for child chunks"
  default     = 500
}

# Semantic Chunking Variables
variable "semantic_max_tokens" {
  type        = number
  description = "Maximum tokens for semantic chunking"
  default     = 512
}

variable "semantic_buffer_size" {
  type        = number
  description = "Buffer size for semantic chunking"
  default     = 1
}

variable "semantic_breakpoint_percentile_threshold" {
  type        = number
  description = "Breakpoint percentile threshold for semantic chunking"
  default     = 75
}

variable "bedrock_embedding_model_arn" {
  type        = string
  description = "Embedding model for Knowledge base"
}


variable "allowed_users" {
  description = "users allowed to access storage"
  type        = list(string)
}

variable "cert_body" {
  type        = string
  description = "Entra cert body"
}

variable "cert_pk" {
  type        = string
  description = "Entra cert pk"
}

variable "kb_data_path" {
  type = string
}

variable "number_of_shards" {
  type    = string
  default = "2"
}

variable "number_of_replicas" {
  type    = string
  default = "0"
}

variable "index_knn" {
  type    = bool
  default = true
}

variable "index_knn_algo_param_ef_search" {
  type    = string
  default = "512"
}


variable "vector_index_name" {
  type        = string
  description = "Name for the vector index"
  default     = "bedrock-knowledge-base-default-index"
}


variable "oss_default_vector_config" {
  type = object({
    type      = string
    dimension = number
    method = object({
      name   = string
      engine = string
      parameters = object({
        m               = number
        ef_construction = number
      })
      space_type = string
    })
  })
}


variable "kb_id_manual" {
  type        = string
  description = "knowledge base id for kb created manually from console"
  default     = ""
}
