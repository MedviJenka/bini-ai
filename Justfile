# --------------------------------------------------------------------------------- #
#     > just build bini ........................... (bini:latest)                   #
#     > just build bini dev ........... (bini:dev)                                  #
#     > just build-all                                                              #
# --------------------------------------------------------------------------------- #


set dotenv-load := false

registry := "ghcr.io/medvijenka/bini"

build service tag="dev":
  docker buildx build --file Dockerfile --target {{service}} --tag {{registry}}/{{service}}:{{tag}} --push .

bini:
    just build mcp_service

api:
    just build api_service

proxy:
    just build claude_proxy

list:
    @just --list