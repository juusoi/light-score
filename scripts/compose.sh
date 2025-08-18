#!/usr/bin/env bash
# Portable wrapper over docker/podman compose.
# Usage: [DOCKER=docker|podman] ./scripts/compose.sh [compose args]

set -euo pipefail

ENGINE="${DOCKER:-docker}"
COMPOSE_FILE="${COMPOSE_FILE:-compose.yaml}"

choose_compose() {
  case "$ENGINE" in
    docker)
      if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
        echo "docker compose"
      elif command -v docker-compose >/dev/null 2>&1; then
        echo "docker-compose"
      else
        echo "Error: docker compose or docker-compose not found" >&2
        exit 1
      fi
      ;;
    podman)
      if command -v podman >/dev/null 2>&1 && podman compose version >/dev/null 2>&1; then
        echo "podman compose"
      elif command -v podman-compose >/dev/null 2>&1; then
        echo "podman-compose"
      else
        echo "Error: podman compose or podman-compose not found" >&2
        exit 1
      fi
      ;;
    *)
      echo "Error: unknown engine '$ENGINE'. Set DOCKER=docker or DOCKER=podman" >&2
      exit 1
      ;;
  esac
}

COMPOSE_CMD=$(choose_compose)
exec ${COMPOSE_CMD} -f "${COMPOSE_FILE}" "$@"
