ARG VERSION=3.12-slim

# ----------------------- #
#         Builder         #
# ----------------------- #
FROM python:${VERSION} AS build

WORKDIR /app
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
CMD ["uv", "run", "fastmcp", "run", "main.py:mcp", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "6000"]

FROM node:lts-slim AS dashboard
RUN npm install -g @modelcontextprotocol/inspector
CMD ["npx", "@modelcontextprotocol/inspector", "--server-url", "http://mcp_service:6000/mcp", "--transport", "streamable-http"]
