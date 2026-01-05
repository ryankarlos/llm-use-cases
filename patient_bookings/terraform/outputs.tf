# Outputs for NHS Patient Booking Demo

output "agent_id" {
  description = "Bedrock Agent ID"
  value       = aws_bedrockagent_agent.supervisor.agent_id
}

output "agent_alias_id" {
  description = "Bedrock Agent Alias ID"
  value       = aws_bedrockagent_agent_alias.live.agent_alias_id
}

output "demo_bucket" {
  description = "S3 bucket for demo files"
  value       = aws_s3_bucket.demo.id
}

output "lambda_function" {
  description = "Lambda function name"
  value       = aws_lambda_function.actions.function_name
}

output "env_vars" {
  description = "Environment variables for the demo app"
  value       = <<-EOT
export AWS_REGION=${var.aws_region}
export BEDROCK_AGENT_ID=${aws_bedrockagent_agent.supervisor.agent_id}
export BEDROCK_AGENT_ALIAS_ID=${aws_bedrockagent_agent_alias.live.agent_alias_id}
export AUDIO_BUCKET=${aws_s3_bucket.demo.id}
EOT
}
