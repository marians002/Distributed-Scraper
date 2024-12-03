#!/bin/bash

# Configuración de las redes
CLIENTS_NET="clients"
SERVERS_NET="servers"
CLIENTS_SUBNET="10.0.10.0/24"
SERVERS_SUBNET="10.0.11.0/24"

# Configuración de contenedores
ROUTER_NAME="router"
ROUTER_CLIENTS_IP="10.0.10.254"
ROUTER_SERVERS_IP="10.0.11.254"

SERVER_NAME="server1"
SERVER_IP="10.0.11.2"
SERVER_PORT=5000

CLIENT_IMAGE="client:latest"
SERVER_IMAGE="server:latest"
ROUTER_IMAGE="router:latest"
BASE_IMAGE="server:base"  # Nombre de la imagen base

CLIENT_BASE_IP="10.0.10."
CLIENT_START_PORT=3000
NUM_CLIENTS=1

# Directorios de los Dockerfiles
ROUTER_DIR="./router"
SERVER_DIR="./server"
CLIENT_DIR="./client"
BASE_DIR="./"  # Directorio del Dockerfile base

# Iniciar clientes
echo "Iniciando clientes..."
for i in $(seq 1 $NUM_CLIENTS); do
  CLIENT_NAME="client$i"
  CLIENT_IP="${CLIENT_BASE_IP}$((1 + i))"
  CLIENT_HOST_PORT=$((CLIENT_START_PORT + i - 1))
  echo "Iniciando $CLIENT_NAME en IP $CLIENT_IP y puerto $CLIENT_HOST_PORT..."
  docker run --rm -d --name $CLIENT_NAME --cap-add NET_ADMIN \
    --network $CLIENTS_NET --ip $CLIENT_IP -p $CLIENT_HOST_PORT:3000 $CLIENT_IMAGE || { echo "Error al iniciar el cliente $CLIENT_NAME";  }
done

# Iniciar servidor
echo "Iniciando servidor..."
docker run --rm -d --name $SERVER_NAME --cap-add NET_ADMIN \
  --network $SERVERS_NET --ip $SERVER_IP -p $SERVER_PORT:$SERVER_PORT $SERVER_IMAGE || { echo "Error al iniciar el servidor";   }

# Configura reglas de iptables en el router
echo "Configurando reglas de iptables en el router..."
docker exec $ROUTER_NAME sh -c "iptables -t nat -A PREROUTING -p tcp --dport $SERVER_PORT -j DNAT --to-destination $SERVER_IP:$SERVER_PORT;"
docker exec $ROUTER_NAME sh -c "iptables -t nat -A POSTROUTING -j MASQUERADE"

# Reglas de iptables para los clientes
for i in $(seq 1 $NUM_CLIENTS); do
  CLIENT_IP="10.0.10.$((1 + i))"
  CLIENT_PORT=$((CLIENT_START_PORT + i - 1))
  echo "Configurando iptables para cliente$i en puerto $CLIENT_PORT..."
  docker exec $ROUTER_NAME sh -c "
    iptables -t nat -A PREROUTING -p tcp --dport $CLIENT_PORT -j DNAT --to-destination $CLIENT_IP:3000;
  "
done

# Mensajes de éxito y accesos
echo "Sistema levantado con éxito!"
echo "Accede a los contenedores desde:"
for i in $(seq 1 $NUM_CLIENTS); do
  CLIENT_IP="${CLIENT_BASE_IP}$((1 + i))"
  CLIENT_HOST_PORT=$((CLIENT_START_PORT + i - 1))
  echo "  Cliente$i: http://$CLIENT_IP:$CLIENT_HOST_PORT"
done
echo "  Servidor: http://$SERVER_IP:$SERVER_PORT"
