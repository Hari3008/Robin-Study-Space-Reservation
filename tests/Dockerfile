# syntax=docker/dockerfile:1
# base image to use for application
FROM golang:1.19

# Set destination for COPY
# default dir for subsequent commands
WORKDIR /app

# Download Go modules
# add go.mod and go.sum to image
# COPY two files into target img ./
COPY locust_server/go.mod locust_server/go.sum ./

# Download directories onto image
RUN go mod download
RUN apt-get update && apt-get install -y curl

# Copy the source code. Note the slash at the end, as explained in
# https://docs.docker.com/engine/reference/builder/#copy
# copy source code into the image
COPY *.go ./

# Build
# compile your application
RUN CGO_ENABLED=0 GOOS=linux go build -o /docker-gs-ping

# To bind to a TCP port, runtime parameters must be supplied to the docker command.
# But we can (optionally) document in the Dockerfile what ports
# the application is going to listen on by default.
# https://docs.docker.com/engine/reference/builder/#expose
EXPOSE 8080

# Run
#  tell Docker what command to run when your image is used
CMD [ "/locust_server" ]
