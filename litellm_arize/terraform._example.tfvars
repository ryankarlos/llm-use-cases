# LiteLLM ECS Demo - Terraform Variables
# Secrets are auto-generated and stored in Secrets Manager

env          = "dev"
project_name = "litellm-demo"

tag = {
  name = "litellm-demo"
}

# IP whitelist - used for both ALB security group and WAF
# replace with your ip
allowed_cidr_blocks = [<YOUR-IP>/32]

# WAF rate limit (requests per 5 minutes per IP) for DDoS protection
waf_rate_limit = 2000

# Phoenix observability
phoenix_api_key      = "youur-phoenix-apui-key"
phoenix_project_name = "aws_litellm_demo"

# Aurora scaling (reduced for demo)
aurora_scaling_config = {
  min_capacity = 0.5
  max_capacity = 2
}

# Skip final snapshot for easier cleanup
skip_final_snapshot = true

# LiteLLM API key (replace this with actual key after you generate once litellm is deployed)
litellm_api_key = "sk-litellm-demo-key"

gemini_api_key = "gemnini-dummy-secret"

# Phoenix collector endpoint
phoenix_collector_endpoint = "<ENTER YOUR PHOENIX ENDPOINT>"
