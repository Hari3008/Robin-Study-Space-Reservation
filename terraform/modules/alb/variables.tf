# modules/alb/variables.tf

variable "service_name" {
  description = "Name of the service"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where ALB will be created"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for ALB (should be public subnets)"
  type        = list(string)
}

variable "container_port" {
  description = "Port that the container listens on"
  type        = number
}

variable "ecs_security_group_id" {
  description = "Security group ID of the ECS tasks to allow ALB traffic"
  type        = string
}

