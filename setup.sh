#!/usr/bin/env bash
set -euo pipefail

log() { echo -e "\n==> $*"; }
warn() { echo -e "\nWARNING: $*" >&2; }

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root via sudo: sudo bash $0" >&2
  exit 1
fi

TARGET_USER="${SUDO_USER:-}"
if [[ -z "${TARGET_USER}" || "${TARGET_USER}" == "root" ]]; then
  warn "Couldn't determine non-root user (SUDO_USER empty). docker group step will be skipped."
fi

log "[0] Check nvidia-smi"
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi
else
  warn "nvidia-smi not found (drivers likely not installed)."
fi

log "[1] apt update"
apt-get update -y

log "Install packages (docker.io, docker-compose-v2, tigervnc-viewer, toolkit deps)"
apt-get install -y \
  docker.io \
  docker-compose-v2 \
  tigervnc-viewer \
  ca-certificates \
  curl \
  gnupg2

log "Install gdown (needed by get_game.sh)"
python3 -m pip install -U gdown

log "Enable/start Docker"
systemctl enable --now docker || true

log "[3] Docker group setup (docker without sudo)"
groupadd -f docker
if [[ -n "${TARGET_USER}" && "${TARGET_USER}" != "root" ]]; then
  usermod -aG docker "${TARGET_USER}"
  warn "Added ${TARGET_USER} to docker group. Log out/in (or reboot) for this to apply."
else
  warn "Skipping usermod -aG docker because TARGET_USER is unknown."
fi

log "Install NVIDIA Container Toolkit repo key + list"
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | tee /etc/apt/sources.list.d/nvidia-container-toolkit.list > /dev/null

log "apt update (after adding NVIDIA repo)"
apt-get update -y

log "Install NVIDIA Container Toolkit (pinned)"
NVIDIA_CONTAINER_TOOLKIT_VERSION="1.18.2-1"
apt-get install -y \
  "nvidia-container-toolkit=${NVIDIA_CONTAINER_TOOLKIT_VERSION}" \
  "nvidia-container-toolkit-base=${NVIDIA_CONTAINER_TOOLKIT_VERSION}" \
  "libnvidia-container-tools=${NVIDIA_CONTAINER_TOOLKIT_VERSION}" \
  "libnvidia-container1=${NVIDIA_CONTAINER_TOOLKIT_VERSION}"

log "Configure NVIDIA runtime for Docker + restart Docker"
nvidia-ctk runtime configure --runtime=docker

log "Restart Docker"
systemctl restart docker

log "Done."
warn "If you just enabled docker group access, log out/in (or reboot) before running docker without sudo."
