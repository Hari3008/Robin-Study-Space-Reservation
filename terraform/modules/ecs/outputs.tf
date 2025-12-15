# ECS Cluster Name
output "cluster_name" {
  description = "ECS Cluster Name"
  value       = aws_ecs_cluster.this.name
}

# ECS Service Name
output "service_name" {
  description = "ECS Service Name"
  value       = aws_ecs_service.this.name
}

# ECS Task Definition ARN
output "task_definition_arn" {
  description = "ARN of the ECS Task Definition"
  value       = aws_ecs_task_definition.this.arn
}

# (Optional) ECS Service ARN
output "service_arn" {
  description = "ARN of the ECS Service"
  value       = aws_ecs_service.this.arn
}
