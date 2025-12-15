# -------------------------
# Build stage
# -------------------------
FROM golang:1.25.1-alpine AS builder

# Set working directory
WORKDIR /app

# Copy Go modules manifests and download dependencies
COPY go.mod go.sum ./
RUN go mod download

# Copy the rest of the source code
COPY . .

# Build the Go binary
RUN go build -o user-service .

# -------------------------
# Run stage
# -------------------------
FROM alpine:3.18

# Set working directory
WORKDIR /app

# Copy the binary from the builder stage
COPY --from=builder /app/user-service .

# Expose container port (matches ECS target group)
EXPOSE 8080

# Default command to run the binary
CMD ["./user-service"]