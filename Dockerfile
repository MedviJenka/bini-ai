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
#    Frontend Builder     #
# ----------------------- #
FROM node:20-alpine AS frontend_base

WORKDIR /app

ARG REACT_APP_SYSTEM_SERVICE
ARG REACT_APP_BINI_SERVICE

ENV REACT_APP_SYSTEM_SERVICE=${REACT_APP_SYSTEM_SERVICE}
ENV REACT_APP_BINI_SERVICE=${REACT_APP_BINI_SERVICE}

COPY frontend/app/package*.json ./
RUN npm install

COPY frontend/app ./
RUN npm run build

# ----------------------- #
#       Run Service       #
# ----------------------- #

#FROM node:20-alpine AS frontend_service
#COPY --from=frontend_base /app ./
#CMD ["npm", "start", "--port", "3000"]

FROM build AS bini_service
CMD ["uv", "run", "uvicorn", "services.bini:app", "--host", "0.0.0.0", "--port", "8081", "--workers", "4"]

FROM build AS rc
CMD ["uv", "run", "uvicorn", "services.bini:app", "--host", "0.0.0.0", "--port", "8082", "--workers", "4"]

#FROM build AS system_service
#CMD ["uv", "run", "uvicorn", "services.system:app", "--host", "0.0.0.0", "--port", "8082"]
