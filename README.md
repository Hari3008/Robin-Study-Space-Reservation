# SpaceRush - Study Space Reservation System

We aim to build a scalable study space reservation platform for Northeastern University that improves on the current Robin app experience. Students frequently encounter limited availability information, sluggish load times during peak hours, and minimal visibility into upcoming reservations. A modernized system with elastic back-end services, richer analytics, and proactive notifications will help students find and manage study spaces efficiently, while giving campus operations better insight into usage patterns.

Deliver a functional MVP that supports core booking flows (search, reserve, modify, cancel) for Northeastern study spaces, instrument the platform with metrics to judge consistency and latency targets, and document experiment results that validate the system’s reliability under projected student usage. Operate a campus-wide reservations utility that can scale to other universities, complete with predictive analytics for space utilization, cross-campus resource sharing, and a plug-in architecture that supports new modalities like smart lock integrations and IoT occupancy sensing.

## Overview

This system allows students to discover, book, and manage study space reservations across campus buildings. The architecture prioritizes **consistency over availability** ensuring no double-bookings occur even under high concurrent load—while maintaining sub-second response times for typical operations.

## Features

- **User Management**: Registration, authentication, and session management
- **Space Management**: Admin creation of buildings, floors, and bookable spaces
- **Reservation System**: Book, view, and cancel study space reservations
- **Conflict Prevention**: Atomic operations prevent double-booking of time slots
- **Horizontal Scaling**: Auto-scaling based on CPU/memory utilization
- **Fault Tolerance**: Graceful handling of service failures with automatic recovery

## Architecture

### Services

| Service | Description | Port |
|---------|-------------|------|
| User Service | Handles user registration, login, and session validation | 8080 |
| Space Service | Manages buildings, floors, and study spaces | 8081 |
| Booking Service | Processes reservations with conflict detection | 8082 |

### Tech Stack

- **Language**: Go 1.21+
- **Database**: Amazon DynamoDB (with GSI for date-based queries)
- **Container Orchestration**: AWS ECS Fargate
- **Load Balancer**: AWS Application Load Balancer
- **Infrastructure**: Terraform
- **Monitoring**: AWS CloudWatch
- **Load Testing**: Locust

### Infrastructure Components

- **VPC** with public and private subnets across 2 availability zones
- **Application Load Balancer** for traffic distribution and health checks
- **ECS Cluster** running Fargate tasks (no EC2 management)
- **DynamoDB Tables**: Users, Spaces, Bookings (with DateIndex GSI)
- **ECR Repositories** for container images
- **CloudWatch** for logs, metrics, and alarms

## API Endpoints

### User Service

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/user` | Create new user |
| POST | `/user/{id}` | Login (returns session token) |
| GET | `/user/{id}` | Get user details |
| DELETE | `/user/{id}` | Delete user |

### Space Service

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/space` | Create new space (admin only) |
| GET | `/space` | List all spaces |
| GET | `/space/{id}` | Get space details |
| GET | `/space/{id}/availability` | Check availability for date |
| DELETE | `/space/{id}` | Delete space (admin only) |

### Booking Service

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/booking` | Create reservation |
| GET | `/booking/{id}` | Get booking details |
| GET | `/booking/user/{userId}` | Get user's bookings |
| DELETE | `/booking/{id}` | Cancel reservation |

## Getting Started

### Prerequisites

- Go 1.21 or higher
- Docker and Docker Compose
- AWS CLI configured with appropriate credentials
- Terraform 1.0+

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/Hari3008/robin-study-space-reservation.git
cd study-space-reservation
```

2. Start local DynamoDB:
```bash
docker-compose up -d dynamodb-local
```

3. Run services locally:
```bash
cd services/user-service && go run main.go &
cd services/space-service && go run main.go &
cd services/booking-service && go run main.go &
```

4. Test the API:
```bash
# Create a user
curl -X POST http://localhost:8080/user \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "userPassword": "password123"}'

# Login
curl -X POST http://localhost:8080/user/{userId} \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "userPassword": "password123"}'
```

### AWS Deployment

1. Initialize Terraform:
```bash
cd terraform
terraform init
```

2. Review the deployment plan:
```bash
terraform plan
```

3. Deploy infrastructure:
```bash
terraform apply
```

4. Get the ALB URL:
```bash
terraform output alb_url
```

5. Test the deployed API:
```bash
export API_URL=$(terraform output -raw alb_url)
curl $API_URL/health
```

### Teardown

```bash
terraform destroy
```

### Load Testing with Locust

1. Install Locust:
```bash
pip install locust
```

2. Run load tests:
```bash
cd locust
locust -f locust_file.py --host=http://your-alb-url
```

3. Or use Docker Compose for distributed testing:
```bash
docker-compose -f docker-compose.locust.yml up --scale worker=4
```

Access Locust UI at `http://localhost:8089`

### Burst Testing

Run the Go-based burst test for concurrent booking experiments:
```bash
cd tests
go run burst_test.go
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_REGION` | AWS region for DynamoDB | `us-west-2` |
| `DYNAMODB_ENDPOINT` | DynamoDB endpoint (for local dev) | - |
| `PORT` | Service port | `8080` |

### Terraform Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `project_name` | Prefix for all resources | `study-reservation` |
| `aws_region` | AWS region | `us-west-2` |
| `app_count` | Number of ECS tasks | `2` |
| `min_capacity` | Minimum tasks for auto-scaling | `2` |
| `max_capacity` | Maximum tasks for auto-scaling | `10` |

## Results

The experimental results are present in the assets folder [ExperimentsWriteup.pdf](https://github.com/Hari3008/Robin-Study-Space-Reservation/blob/main/assets/ExperimentsWriteup.pdf)

## Monitoring

### CloudWatch Metrics

- **ECS**: CPU utilization, memory utilization, running task count
- **ALB**: Request count, target response time, HTTP 5xx errors
- **DynamoDB**: Read/write capacity units, throttled requests

## Lessons Learned

1. **Consistency vs Speed**: DynamoDB conditional writes prevent double-bookings but add latency. For financial transactions, correctness wins.

2. **Test on Real AWS**: LocalStack showed 600ms latency; actual AWS showed 45ms. Always performance test on production infrastructure.

3. **GSIs Aren't Free**: Our DateIndex GSI caused read amplification under heavy load. Design indexes carefully.

4. **Design for Failure**: ECS fault tolerance testing proved the system survives container failures with minimal user impact.

## Future Improvements

- [ ] Implement notification service (SQS/SNS) for booking confirmations
- [ ] Implement rate limiting per user
- [ ] Add Prometheus/Grafana for enhanced monitoring
