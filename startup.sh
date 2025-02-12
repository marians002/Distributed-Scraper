#!/bin/bash

# Function to check if a Docker network exists
network_exists() {
    docker network ls --format '{{.Name}}' | grep -q "^$1$"
}

# Function to check if a Docker image exists
image_exists_timage_exists_tagag() {
    IMAGE_NAME=$1
    IMAGE_TAG=$2

    if [ $(docker images -q ${IMAGE_NAME}:${IMAGE_TAG}) ]; then
        return 0  # Image exists
    else
        return 1  # Image does not exist
    fi
}

# Function to check if a Docker image exists
image_exists() {
    docker images --format '{{.Repository}}' | grep -q "^$1$"
}

# Restart Docker service
sudo systemctl restart docker

# Create networks if they don't exist
if ! network_exists "clients"; then
    echo "Creating network 'clients'..."
    docker network create clients --subnet 10.0.10.0/24
else
    echo "Network 'clients' already exists."
fi

if ! network_exists "servers"; then
    echo "Creating network 'servers'..."
    docker network create servers --subnet 10.0.11.0/24
else
    echo "Network 'servers' already exists."
fi

# Check and build router:base image
ROUTER_BASE_TAG="base"
if ! image_exists_tag "router" "$ROUTER_BASE_TAG"; then
    echo "Building router_base image..."
    docker build -t router:$ROUTER_BASE_TAG -f router/router_base.Dockerfile .
else
    echo "Router:base image already exists."
fi

# Check and build router image
ROUTER_TAG="latest"
if ! image_exists_tag "router" "$ROUTER_TAG"; then
    echo "Building router image..."
    docker build -t router:$ROUTER_TAG -f router/router.Dockerfile .
else
    echo "Router image already exists."
fi

# Check if the router container is already running
if [ $(docker ps -q -f name=router) ]; then
    echo "Router container is already running."
else
    echo "Running router container..."
    docker run -itd --rm --name router router
fi

echo "Connecting router to networks..."
docker network connect --ip 10.0.10.254 clients router
docker network connect --ip 10.0.11.254 servers router

# Check and build client_base image
if ! image_exists "client_base"; then
    echo "Building client_base image..."
    docker build -t client_base -f client/Dockerfile.base .
else
    echo "Client_base image already exists."
fi

# Check and build client image
if ! image_exists "client"; then
    echo "Building client image..."
    docker build -t client -f client/client.Dockerfile .
else
    echo "Client image already exists."
fi

# Check and build server_base image
if ! image_exists "server_base"; then
    echo "Building server_base image..."
    docker build -t server_base -f server/Dockerfile.base .
else
    echo "Server_base image already exists."
fi

# Check and build server image
if ! image_exists "server"; then
    echo "Building server image..."
    docker build -t server -f server/server.Dockerfile .
else
    echo "Server image already exists."
fi

# Run server container
echo "Running server container..."
docker run --rm -d --name server1 --cap-add NET_ADMIN --network servers server

# Run client container
echo "Running client container..."
docker run --rm -d --name client1 --cap-add NET_ADMIN --network clients client

# Inspect behavior of server1
echo "Inspecting server1 logs..."
docker logs -f server1