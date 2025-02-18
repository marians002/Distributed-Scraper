#!/bin/bash

echo "Running setup"
chmod +x ./multicast/setup_infra.sh
./multicast/setup_infra.sh

chmod +x ./chord/start_chord.sh
./chord/start_chord.sh


# Function to check if a Docker image exists
image_exists() {
    docker images --format '{{.Repository}}' | grep -q "^$1$"
}


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


# Run client container
echo "Running client container..."
docker run --rm -d --name client1 -v ./client/:/app/ --cap-add NET_ADMIN --network clients client

# Inspect behavior of client1
echo "Inspecting chord1 logs..."
docker logs -f chord1