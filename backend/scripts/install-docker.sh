#!/usr/bin/env bash
#
# Idempotent Docker Engine installer for Ubuntu / Debian (the GCP free-tier
# defaults). Safe to run more than once: if Docker is already installed and
# functional, the script exits without changing anything.
#
# After a fresh install you must log out and back in so your shell picks up
# the new `docker` group membership before `docker` works without sudo.

set -euo pipefail

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    echo "Docker is already installed and running:"
    docker --version
    exit 0
fi

if ! command -v lsb_release >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y lsb-release
fi

DISTRO_ID="$(lsb_release -is | tr '[:upper:]' '[:lower:]')"
DISTRO_CODENAME="$(lsb_release -cs)"

case "$DISTRO_ID" in
    ubuntu|debian) ;;
    *)
        echo "Unsupported distribution: $DISTRO_ID. This script handles ubuntu and debian only." >&2
        exit 1
        ;;
esac

echo "Installing Docker Engine for $DISTRO_ID ($DISTRO_CODENAME)..."

sudo apt-get update
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL "https://download.docker.com/linux/${DISTRO_ID}/gpg" \
    | sudo gpg --dearmor --yes -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

ARCH="$(dpkg --print-architecture)"
echo "deb [arch=${ARCH} signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/${DISTRO_ID} ${DISTRO_CODENAME} stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

sudo apt-get update
sudo apt-get install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin

sudo systemctl enable --now docker

if [ -n "${SUDO_USER:-}" ]; then
    TARGET_USER="$SUDO_USER"
else
    TARGET_USER="$USER"
fi

if ! getent group docker | grep -q "\b${TARGET_USER}\b"; then
    sudo usermod -aG docker "$TARGET_USER"
    echo
    echo "Added ${TARGET_USER} to the 'docker' group."
    echo "Log out and back in (or run 'newgrp docker') for the change to take effect."
fi

echo
echo "Docker installed:"
docker --version
docker compose version
