output "alb_dns_name" {
  description = "The DNS name of the load balancer"
  value       = module.load_balancer.dns
}

output "alb_arn" {
  description = "The ARN of the load balancer"
  value       = module.load_balancer.arn
}

output "ecs_cluster_id" {
  description = "The ID of the ECS cluster"
  value       = module.ecs.cluster_id
}

output "ecs_cluster_arn" {
  description = "The ARN of the ECS cluster"
  value       = module.ecs.cluster_arn
}

output "ecs_service_id" {
  description = "The ID of the ECS service"
  value       = module.ecs.service_id
}

output "ecs_task_definition_arn" {
  description = "The ARN of the Task Definition"
  value       = module.ecs.task_definition_arn
}
