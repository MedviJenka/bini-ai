#!/bin/bash

# ---------------------------------------- #
#      Ubuntu Post-Install Automation      #
#      Docker + SSH + Networking Fix       #
# ---------------------------------------- #

set -e

USER_NAME=${SUDO_USER:-"ubuntu"}
DOCKER_DAEMON_FILE="/etc/docker/daemon.json"
CUSTOM_DOCKER_NETWORK_BIP="172.20.0.1/16"

echo "🚀 Starting Ubuntu post-install setup..."

# --- Update System ---
echo "📦 Updating system packages..."
sudo apt update -y && sudo apt upgrade -y

# --- Install SSH Server ---
echo "🔐 Installing and enabling SSH..."
sudo apt install openssh-server -y
sudo systemctl enable ssh
sudo systemctl start ssh

echo "install vim"
sudo apt install vim -y

# --- Install Docker & Compose ---
echo "🐳 Installing Docker + Docker Compose..."
sudo apt install -y docker.io docker-compose
sudo systemctl enable docker
sudo systemctl start docker

# --- Disable default 172.17.0.0 network & configure pools ---
echo "🌐 Updating Docker daemon network config..."

sudo bash -c "cat > $DOCKER_DAEMON_FILE" <<EOF
{
  "bip": "${CUSTOM_DOCKER_NETWORK_BIP}",
  "default-address-pools": [
    {
      "base": "172.30.0.0/16",
      "size": 24
    },
    {
      "base": "172.31.0.0/16",
      "size": 24
    }
  ]
}
EOF

echo "🔄 Restarting Docker service..."
sudo systemctl restart docker

# --- Add user to docker group ---
echo "👤 Adding $USER_NAME to Docker group..."
sudo usermod -aG docker "$USER_NAME"

echo "ℹ️ Logout and login again for group changes to apply"
echo "Run: groups  (confirm docker group appears)"

# --- Example volume create instruction ---
echo "📦 Creating example named volume: anythingllm_anythingllm_data"
docker volume create anythingllm_anythingllm_data

echo "🧾 Current volumes:"
docker volume ls

# --- Summary ---
echo ""
echo "🎉 Setup Complete!"
echo "Next steps:"
echo " - Logout & login to apply docker permissions"
echo " - Use 'docker compose up -d' to start services"
echo ""
echo "Example external volume configuration for compose.yml:"
echo "
services:
  anythingllm-mi-st:
    container_name: anythingllm-mi-st
    volumes:
      - anythingllm_anythingllm_data:/app/server/storage
      - /opt/anythingllm/main:/backup
    restart: unless-stopped

volumes:
  anythingllm_anythingllm_data:
    external: true
"


# =======================================
# Docker Swarm + Portainer Installation
# =======================================

set -e

echo "🐳 Initializing Docker Swarm..."

# Detect server IP automatically
SERVER_IP=$(hostname -I | awk '{print $1}')

docker swarm init --advertise-addr "$SERVER_IP"

echo "🌐 Swarm initialized on IP: $SERVER_IP"
echo ""
echo "📋 Worker join command:"
docker swarm join-token worker | sed '1!d'
echo ""
echo "📋 Manager join command:"
docker swarm join-token manager | sed '1!d'

echo "🚀 Deploying Portainer to manage the cluster..."

docker volume create portainer_data

docker stack deploy -c - portainer <<EOF
version: "3.9"

services:
  portainer:
    image: portainer/portainer-ce:latest
    ports:
      - "9000:9000"
      - "9443:9443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - portainer_data:/data
    deploy:
      mode: replicated
      replicas: 1
      restart_policy:
        condition: on-failure

volumes:
  portainer_data:
    external: true
EOF

echo ""
echo "🎉 Docker Swarm & Portainer installed successfully"
echo "🔑 Access Portainer UI:"
echo "     https://$SERVER_IP:9443"
echo ""
echo "💡 Add workers using the join command printed above."
