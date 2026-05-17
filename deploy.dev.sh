#!/bin/bash

$SERVICE="rc"

echo "Logging into Azure Container Registry"
az acr login --name biniai

echo "Building and pushing $SERVICE"
docker buildx bake $SERVICE --push

echo "Deploying $SERVICE"
docker stack deploy --compose-file deploy.dev.yaml --with-registry-auth --resolve-image=always dev
echo "Verifying deployment of $SERVICE"

echo "Logs"
docker service ls
docker ps
