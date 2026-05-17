#!/bin/bash

SERVICES="bini_service"
echo "Logging into Azure Container Registry"
az acr login --name biniai

echo "Building and pushing $SERVICE"
docker buildx bake -f docker-bake.hcl $SERVICE --push

echo "Deploying $SERVICE"
docker stack deploy --compose-file deploy.prod.yaml --with-registry-auth --resolve-image=always --detach=false production
echo "Verifying deployment of $SERVICE"

echo "Logs"
docker service ps production_bini_service --no-trunc
docker buildx imagetools inspect biniai.azurecr.io/bini/bini-service:latest
docker service ls
docker ps

