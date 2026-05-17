#!/bin/bash
git add .
git stash
git pull --rebase
docker system prune -af
docker compose up -d --build
