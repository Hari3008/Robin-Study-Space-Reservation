# Region to deploy into
variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "service_name" {
  type    = string
  default = "CS6650L2"
  description = "Base name for shared resources"
}

# Container settings
variable "container_port" {
  type    = number
  default = 8080
  description = "Port for the web service (receiver)"
}

# ECS counts - might want separate counts for each service
variable "ecs_count" {
  type    = number
  default = 2
  description = "Number of receiver tasks"
}

variable "processor_count" {
  type    = number
  default = 1
  description = "Number of processor tasks"
}

# Log retention
variable "log_retention_days" {
  type    = number
  default = 7
}

# ECR repository names - not needed if hardcoded in module call
# variable "ecr_repository_name" {  # Remove if not using
#   type    = string
#   default = "ecr_service"
# }


