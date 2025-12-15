variable "repository_name_user" {
  description = "Name of the ECR repository for User Service"
  type        = string
}

variable "repository_name_booking" {
  description = "Name of the ECR repository for Booking Service"
  type        = string
}

variable "repository_name_availability" {
  description = "Name of the ECR repository for Availability Service"
  type        = string
}

variable "create_processor_repo" {
  description = "Whether to create processor repository"
  type        = bool
  default     = true
}
