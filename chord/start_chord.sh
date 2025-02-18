# Function to check if a Docker image exists
image_exists() {
    docker images --format '{{.Repository}}' | grep -q "^$1$"
}
# Check and build server_base image
if ! image_exists "chord_base"; then
    echo "Building chord_base image..."
    docker build -t chord_base -f chord/Dockerfile.base .
else
    echo "Chord_base image already exists."
fi

# Check and build server image
if ! image_exists "chord"; then
    echo "Building chord image..."
    docker build -t chord -f chord/chord.Dockerfile .
else
    echo "Chord image already exists."
fi


# Run chord container
echo "Running chord container..."
docker run -d --name chord1 -v ./chord/:/app/ --cap-add NET_ADMIN --network servers chord
docker run -d --name chord2 -v ./chord/:/app/ --cap-add NET_ADMIN --network servers chord
docker run -d --name chord3 -v ./chord/:/app/ --cap-add NET_ADMIN --network servers chord


# Inspect behavior of client1
echo "Inspecting chord1 logs..."
docker logs -f chord1