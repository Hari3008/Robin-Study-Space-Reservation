# ECS Cluster Name
output "ecs_cluster_name" {
  value = module.ecs_user.cluster_name
}

# ECS Service Names
output "ecs_service_name" {
  value = {
    user        = module.ecs_user.service_name
    booking     = module.ecs_booking.service_name
    availability = module.ecs_availability.service_name
  }
}

# ECS Task ARNs
output "ecs_task_arns" {
  value = {
    user        = module.ecs_user.task_definition_arn
    booking     = module.ecs_booking.task_definition_arn
    availability = module.ecs_availability.task_definition_arn
  }
}

