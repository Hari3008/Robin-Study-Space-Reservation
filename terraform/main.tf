# Wire together four focused modules: network, ecr, logging, ecs.

module "network" {
  source         = "./modules/network"
  service_name   = var.service_name
  container_port = var.container_port
  alb_sg_id = module.alb.alb_security_group_id
}

module "ecr" {
  source = "./modules/ecr"
  repository_name_user        = "user-service"
  repository_name_booking     = "booking-service"
  repository_name_availability = "availability-service"
}


module "logging" {
  source            = "./modules/logging"
  service_name      = var.service_name
  retention_in_days = var.log_retention_days
}

# Reuse an existing IAM role for ECS tasks
# Required Policies: AmazonECSTaskExecutionRolePolicy, AmazonDynamoDBFullAccess
data "aws_iam_role" "lab_role" {
  name = "MyRole"
}


module "alb" {
  source = "./modules/alb"

  service_name         = var.service_name
  vpc_id               = module.network.vpc_id
  subnet_ids           = module.network.public_subnet_ids
  ecs_security_group_id = module.network.ecs_security_group_id
  container_port       = var.container_port
}

module "dynamodb" {
  source             = "./modules/dynamodb"
}


# --- User Service ---
module "ecs_user" {
  source                = "./modules/ecs"
  service_name          = "${var.service_name}-user-service"
  image                 = docker_registry_image.user.name
  container_port        = var.container_port
  vpc_id                = module.network.vpc_id
  private_subnet_ids    = module.network.private_subnet_ids
  ecs_security_group_id = module.network.ecs_security_group_id
  execution_role_arn    = data.aws_iam_role.lab_role.arn
  task_role_arn         = data.aws_iam_role.lab_role.arn
  log_group_name        = "/ecs/user-service"
  ecs_count             = var.ecs_count
  region                = var.aws_region
  target_group_arn      = module.alb.target_group_arn_user

  environment = [
    { name = "AWS_REGION", value = var.aws_region }
  ]

  depends_on = [module.alb]
}

# --- Availability Service ---
module "ecs_availability" {
  source                = "./modules/ecs"
  service_name          = "${var.service_name}-availability-service"
  image                 = docker_registry_image.availability.name
  container_port        = var.container_port
  vpc_id                = module.network.vpc_id
  private_subnet_ids    = module.network.private_subnet_ids
  ecs_security_group_id = module.network.ecs_security_group_id
  execution_role_arn    = data.aws_iam_role.lab_role.arn
  task_role_arn         = data.aws_iam_role.lab_role.arn
  log_group_name        = "/ecs/availability-service"
  ecs_count             = var.ecs_count
  region                = var.aws_region
  target_group_arn      = module.alb.target_group_arn_availability

  environment = [
    { name = "USER_SERVICE_URL", value = "http://${module.alb.alb_dns_name}/user" },
    { name = "AWS_REGION", value = var.aws_region }
  ]

  depends_on = [module.alb]
}

# --- Space Booking Service ---
module "ecs_booking" {
  source                = "./modules/ecs"
  service_name          = "${var.service_name}-booking-service"
  image                 = docker_registry_image.booking.name
  container_port        = var.container_port
  vpc_id                = module.network.vpc_id
  private_subnet_ids    = module.network.private_subnet_ids
  ecs_security_group_id = module.network.ecs_security_group_id
  execution_role_arn    = data.aws_iam_role.lab_role.arn
  task_role_arn         = data.aws_iam_role.lab_role.arn
  log_group_name        = "/ecs/booking-service"
  ecs_count             = var.ecs_count
  region                = var.aws_region
  target_group_arn      = module.alb.target_group_arn_booking

  environment = [
    { name = "USER_SERVICE_URL", value = "http://${module.alb.alb_dns_name}/user" },
    { name = "AVAIL_SERVICE_URL", value = "http://${module.alb.alb_dns_name}/space" },
    { name = "AWS_REGION", value = var.aws_region }
  ]

  depends_on = [module.alb]
}

# Build User Service image
resource "docker_image" "user" {
  name = "${module.ecr.user_repository_url}:latest"
  build { context = "../services/dynamo_db/user-service" }        # change for different DB
}

resource "docker_registry_image" "user" {
  name = docker_image.user.name
}

# Build Booking Service image
resource "docker_image" "booking" {
  name = "${module.ecr.booking_repository_url}:latest"
  build { context = "../services/dynamo_db/booking-service" }    # change for different DB
}

resource "docker_registry_image" "booking" {
  name = docker_image.booking.name
}

# Build Availability Service image
resource "docker_image" "availability" {
  name = "${module.ecr.availability_repository_url}:latest"
  build { context = "../services/dynamo_db/availability-service" }   # change for different DB
}

resource "docker_registry_image" "availability" {
  name = docker_image.availability.name
}
