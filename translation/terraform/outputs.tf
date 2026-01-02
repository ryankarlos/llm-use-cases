output "dashboard_url" {
  description = "URL to the CloudWatch dashboard"
  value       = var.create_dashboard ? "https://${data.aws_region.current.name}.console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#dashboards:name=${var.dashboard_name}" : null
}

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = var.lambda_function_name
}
