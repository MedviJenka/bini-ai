# --------------------------------------------------------------------------------- #
#     > just build bini ........................... (bini:latest)       #
#     > just build bini dev ........... (bini:dev)          #
#     > just build-all                                                              #
# --------------------------------------------------------------------------------- #


set dotenv-load := false
set shell := ["cmd", "/c"]

registry := "ghcr.io/medvijenka/bini"

build service tag="dev":
  docker buildx build --file Dockerfile --target {{service}} --tag {{registry}}/{{service}}:{{tag}} --push .

bini:
    just build mcp_service

api:
    just build api_service

list:
    @just --list