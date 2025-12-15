# -------------------------------
# ECR Outputs
# -------------------------------

# --- User Service ECR ---
output "user_repository_url" {
  description = "The repository URL for the User Service ECR"
  value       = aws_ecr_repository.user.repository_url
}

output "user_repository_arn" {
  description = "The ARN of the User Service ECR repository"
  value       = aws_ecr_repository.user.arn
}

output "user_repository_name" {
  description = "The name of the User Service ECR repository"
  value       = aws_ecr_repository.user.name
}

# --- Booking Service ECR ---
output "booking_repository_url" {
  description = "The repository URL for the Booking Service ECR"
  value       = aws_ecr_repository.booking.repository_url
}

output "booking_repository_arn" {
  description = "The ARN of the Booking Service ECR repository"
  value       = aws_ecr_repository.booking.arn
}

output "booking_repository_name" {
  description = "The name of the Booking Service ECR repository"
  value       = aws_ecr_repository.booking.name
}

# --- Availability Service ECR ---
output "availability_repository_url" {
  description = "The repository URL for the Availability Service ECR"
  value       = aws_ecr_repository.availability.repository_url
}

output "availability_repository_arn" {
  description = "The ARN of the Availability Service ECR repository"
  value       = aws_ecr_repository.availability.arn
}

output "availability_repository_name" {
  description = "The name of the Availability Service ECR repository"
  value       = aws_ecr_repository.availability.name
}
