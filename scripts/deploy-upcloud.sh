#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="${HOME}/light-score"
cd "${TARGET_DIR}"

IMAGE_TAG="${IMAGE_TAG:-latest}"
export IMAGE_TAG

echo "📦 Pulling images for tag: ${IMAGE_TAG}..."
podman compose -f compose.prod.yaml pull

echo "🚀 Restarting stack with rootless Podman..."
podman compose -f compose.prod.yaml up -d --remove-orphans

echo "⏳ Verifying service health..."
HEALTHY=false
for i in $(seq 1 15); do
  if curl -sf http://127.0.0.1:5000/ > /dev/null 2>&1; then
    echo "✅ Health check passed: http://127.0.0.1:5000/ is responding (attempt ${i}/15)"
    HEALTHY=true
    break
  fi
  echo "Waiting for frontend to respond (attempt ${i}/15)..."
  sleep 2
done

if [ "$HEALTHY" = false ]; then
  echo "❌ Health check failed after 30 seconds!"
  echo "=== Container logs ==="
  podman compose -f compose.prod.yaml logs --tail 50
  exit 1
fi

echo "✅ UpCloud deployment successful!"
podman ps --filter "name=light-score"
