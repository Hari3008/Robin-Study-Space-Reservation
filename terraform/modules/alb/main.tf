# modules/alb/main.tf
# Application Load Balancer and Target Group for ECS service

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "${var.service_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.subnet_ids

  enable_deletion_protection = false

  tags = {
    Name = "${var.service_name}-alb"
  }
}

# Target Group for ECS tasks
resource "aws_lb_target_group" "user" {
  name        = "${var.service_name}-tg-user"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path     = "/user/health"
    protocol = "HTTP"
  }
}

resource "aws_lb_target_group" "booking" {
  name        = "${var.service_name}-tg-booking"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path     = "/booking/health"
    protocol = "HTTP"
  }
}

resource "aws_lb_target_group" "availability" {
  name        = "${var.service_name}-tg-availability"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path     = "/space/health"
    protocol = "HTTP"
  }
}


# Listener for ALB (HTTP on port 80)
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
  type = "fixed-response"

  fixed_response {
    content_type = "text/plain"
    status_code  = "404"
    message_body = "No routing rule matched"
  }
}

}

resource "aws_lb_listener_rule" "user_rule" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 10

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.user.arn
  }

  condition {
    path_pattern {
      values = ["/user*"]
    }
  }
}

resource "aws_lb_listener_rule" "booking_rule" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 20

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.booking.arn
  }

  condition {
    path_pattern {
      values = ["/booking*"]
    }
  }
}

resource "aws_lb_listener_rule" "availability_rule" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 30

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.availability.arn
  }

  condition {
    path_pattern {
      values = ["/space*"]
    }
  }
}


# Security Group for ALB
resource "aws_security_group" "alb" {
  name        = "${var.service_name}-alb-sg"
  description = "Security group for Application Load Balancer"
  vpc_id      = var.vpc_id

  # Allow HTTP traffic from internet
  ingress {
    description = "HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow all outbound traffic
  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.service_name}-alb-sg"
  }
}

