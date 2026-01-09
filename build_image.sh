#!/bin/bash

  # privacy-manager:
  #   image: privacy-manager:latest
  #   container_name: privacy-manager
  #   restart: unless-stopped
  #   network_mode: "host"
  #   cap_add:
  #     - NET_ADMIN
  #   environment:
  #     - TZ=Europe/Rome

set -e

IMAGE_NAME=privacy-manager
IMAGE_TAG=latest
PLATFORM=linux/arm64

echo "🔨 Building ${IMAGE_NAME}:${IMAGE_TAG} for ${PLATFORM}..."

docker buildx build \
  --platform ${PLATFORM} \
  -t ${IMAGE_NAME}:${IMAGE_TAG} \
  -f docker/Dockerfile-OpenWrt \
  --load \
  .

echo "📦 Exporting image..."
docker save -o ${IMAGE_NAME}.tar ${IMAGE_NAME}:${IMAGE_TAG}

echo "📤 Upload to gateway..."
scp -O ${IMAGE_NAME}.tar root@10.0.1.1:/opt/docker/tmp

echo "💻 SSH into gateway and load image..."
ssh root@10.0.1.1 << 'EOF'
  docker load -i /opt/docker/tmp/privacy-manager.tar
  cd /opt/domo/domo-compose
  docker compose stop privacy-manager
  docker compose up -d privacy-manager
EOF

echo "✅ Done!"
