#!/bin/bash

sudo apt update
sudo apt upgrade -y

# Install prerequisites
sudo apt install apt-transport-https ca-certificates curl software-properties-common -y

# Add Docker's GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update package index
sudo apt update -y

# Install Docker
sudo apt install docker-ce docker-ce-cli containerd.io -y

# install npx
sudo apt install nodejs npm -y

# Add current user to docker group (avoids using sudo)
sudo usermod -aG docker $USER

# Apply the group change (or logout/login)
newgrp docker

sudo apt install docker-compose-plugin -y

# Check Docker version
docker --version

# Check Docker Compose version
docker compose version
# or if using older installation method:
docker-compose --version

# Test Docker
docker run hello-world

sudo systemctl enable docker
sudo systemctl start docker

# EXPERIMENTAL .........................................................................................................

# Create the service file in one command
sudo tee /etc/systemd/system/docker-compose-app.service > /dev/null <<EOF
[Unit]
Description=Docker Compose Application Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ec2-user/your-project-directory
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable docker-compose-app.service
sudo systemctl start docker-compose-app.service

# Check status
sudo systemctl status docker-compose-app.service

# Start Docker daemon
sudo systemctl start docker

# Enable Docker to start on boot
sudo systemctl enable docker

# Check Docker status
sudo systemctl status docker


# Create Docker directory if it doesn't exist
sudo mkdir -p /etc/docker

# Create daemon.json with the configuration
sudo tee /etc/docker/daemon.json > /dev/null << EOF
{
  "insecure-registries": ["mirror.gcr.io", "registry-1.docker.io"],
  "registry-mirrors": ["http://mirror.gcr.io"]
}
EOF

# Restart Docker
sudo systemctl restart docker

echo "Docker daemon.json configured and Docker restarted!"

echo "installing minikube"

# Install Minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
rm minikube-linux-amd64
# Start Minikube
minikube start --driver=docker
# Enable Minikube addons
minikube addons enable ingress dashboard
# Enable Minikube dashboard
minikube dashboard
