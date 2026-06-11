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
CMD ["uv", "run", "fastmcp", "run", "services/mcp_server.py:mcp", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "6000"]

FROM build AS api_service
CMD ["uv", "run", "uvicorn", "services.api:app", "--host", "0.0.0.0", "--port", "6001"]

FROM build AS claude_proxy
RUN apt-get update && \
    apt-get install -y --no-install-recommends nodejs npm && \
    npm install -g @anthropic-ai/claude-code && \
    npm cache clean --force && \
    apt-get purge -y npm && apt-get autoremove -y && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --shell /bin/bash proxy
USER proxy
EXPOSE 8787
CMD ["uv", "run", "python", "-m", "services.claude_proxy"]

FROM node:lts-slim AS dashboard
RUN npm install -g @modelcontextprotocol/inspector
CMD ["npx", "@modelcontextprotocol/inspector", "--server-url", "http://mcp_service:6000/mcp", "--transport", "streamable-http"]
