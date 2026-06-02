ARG VERSION=3.12-slim

# ----------------------- #
#         Builder         #
# ----------------------- #
FROM python:${VERSION} AS build

WORKDIR /app

RUN apt-get update && apt-get install -y ca-certificates curl gnupg && \
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    chmod a+r /etc/apt/keyrings/docker.gpg && \
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
      https://download.docker.com/linux/debian \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
      > /etc/apt/sources.list.d/docker.list && \
    apt-get update && \
    apt-get install -y docker-ce-cli docker-compose-plugin && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
RUN pip install uv
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen
COPY . .


# ----------------------- #
#       Run MVP           #
# ----------------------- #

FROM build AS mcp_service
CMD ["uv", "run", "fastmcp", "run", "services/mcp_server.py:mcp", "--transport", "http", "--host", "0.0.0.0", "--port", "8082"]
