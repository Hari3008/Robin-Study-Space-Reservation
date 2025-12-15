# modules/alb/outputs.tf

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "alb_arn" {
  description = "ARN of the Application Load Balancer"
  value       = aws_lb.main.arn
}

output "target_group_arn_user" {
  description = "ARN of the Target Group"
  value       = aws_lb_target_group.user.arn
}

output "target_group_arn_booking" {
  description = "ARN of the Target Group"
  value       = aws_lb_target_group.booking.arn
}

output "target_group_arn_availability" {
  description = "ARN of the Target Group"
  value       = aws_lb_target_group.availability.arn
}

output "alb_security_group_id" {
  description = "Security group ID of the ALB"
  value       = aws_security_group.alb.id
}

output "alb_zone_id" {
  description = "Zone ID of the ALB (for Route53 if needed)"
  value       = aws_lb.main.zone_id
}