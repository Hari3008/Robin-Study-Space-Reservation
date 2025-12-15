resource "aws_ecr_repository" "user" {
  name = var.repository_name_user
}

resource "aws_ecr_repository" "booking" {
  name = var.repository_name_booking
}

resource "aws_ecr_repository" "availability" {
  name = var.repository_name_availability
}