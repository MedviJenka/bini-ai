# docker buildx bake --push

variable "REGISTRY" {
  default = "biniai.azurecr.io/bini"
}

target "bini_service" {
  context = "."
  dockerfile = "Dockerfile"
  target = "bini_service"
  tags = ["${REGISTRY}/bini-service:latest"]
}

target "rc" {
  context = "."
  dockerfile = "Dockerfile"
  target = "rc"
  tags = ["${REGISTRY}/rc:latest"]
}
