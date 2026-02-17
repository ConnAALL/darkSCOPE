FROM ubuntu:22.04 AS base
ENV DEBIAN_FRONTEND=noninteractive

RUN dpkg --add-architecture i386

# Base dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl gnupg2 wget \
      unzip cabextract xz-utils p7zip-full file \
      bash git vim htop tmux procps psmisc \
      x11-utils x11-xserver-utils xauth \
      xserver-xorg-core \
      xserver-xorg-legacy \
      xserver-xorg-video-dummy \
      xserver-xorg-input-libinput \
      mesa-utils mesa-utils-bin \
      x11vnc \
      vulkan-tools \
      pulseaudio pulseaudio-utils \
      xvfb \
      winbind \
      fonts-wine \
      libvulkan1 libvulkan1:i386 \
      mesa-vulkan-drivers mesa-vulkan-drivers:i386 \
      libdrm2 libdrm2:i386 \
      libgbm1 libgbm1:i386 \
      libgl1 libgl1:i386 \
      libx11-6 libx11-6:i386 \
      libxext6 libxext6:i386 \
      libxcb1 libxcb1:i386 \
      libxrandr2 libxrandr2:i386 \
      libxi6 libxi6:i386 \
      libxfixes3 libxfixes3:i386 \
      libxcursor1 libxcursor1:i386 \
      libxrender1 libxrender1:i386 \
      libfreetype6 libfreetype6:i386 \
      libdbus-1-3 libdbus-1-3:i386 \
      libasound2 libasound2:i386 \
      libpulse0 libpulse0:i386 \
      python3-pip \
    && rm -rf /var/lib/apt/lists/*

# WineHQ repo (Jammy) + Wine stable
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://dl.winehq.org/wine-builds/winehq.key | \
      gpg --dearmor -o /etc/apt/keyrings/winehq-archive.key && \
    curl -fsSL https://dl.winehq.org/wine-builds/ubuntu/dists/jammy/winehq-jammy.sources | \
      sed 's#Signed-By:.*#Signed-By: /etc/apt/keyrings/winehq-archive.key#' \
      > /etc/apt/sources.list.d/winehq-jammy.sources && \
    apt-get update && \
    apt-get install -y --install-recommends winehq-stable && \
    rm -rf /var/lib/apt/lists/*

# Winetricks
RUN wget -qO /usr/local/bin/winetricks \
      https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks && \
    chmod +x /usr/local/bin/winetricks

# Defaults
ENV WINEPREFIX=/opt/prefix \
    WINEARCH=win64 \
    WINEDEBUG=-all \
    GAME_ROOT=/root/Dark.Souls.Remastered.v1.04 \
    WINEESYNC=0 \
    WINEFSYNC=0 \
    WINEDLLOVERRIDES="mscoree,mshtml=;winemenubuilder.exe=d" \
    WINETRICKS_OPT_UNATTENDED=1

# Initialize the Wine prefix
RUN set -eux; \
    mkdir -p "$WINEPREFIX"; \
    export DISPLAY=:99; \
    Xvfb :99 -screen 0 1024x768x24 -nolisten tcp -noreset & \
    xvfb_pid=$!; \
    trap "kill -TERM $xvfb_pid || true; wait $xvfb_pid || true" EXIT; \
    wineboot --init; \
    env WINETRICKS_SUPER_QUIET=1 WINETRICKS_VERBOSE=0 \
      winetricks -q --unattended win10 vcrun2022 d3dcompiler_47; \
    rm -rf /root/.cache/winetricks; \
    wineserver -k || true

# Common application layer
FROM base AS app
WORKDIR /root

COPY Dark.Souls.Remastered.v1.04.zip /root/Dark.Souls.Remastered.v1.04.zip
RUN 7z x -y -o/root /root/Dark.Souls.Remastered.v1.04.zip && rm -f /root/Dark.Souls.Remastered.v1.04.zip

COPY scripts /root/scripts
COPY darkAgent /root/darkAgent

RUN chmod +x /root/scripts/*.sh
RUN python3 -m pip install --no-cache-dir -r /root/darkAgent/requirements.txt

ENTRYPOINT ["/root/scripts/entrypoint.sh"]
CMD ["/bin/bash"]

# iGPU branch
FROM app AS igpu
ARG DXVK_VERSION=2.6.2
RUN set -eux; \
    cd /tmp; \
    wget -q -O dxvk.tar.gz "https://github.com/doitsujin/dxvk/releases/download/v${DXVK_VERSION}/dxvk-${DXVK_VERSION}.tar.gz"; \
    tar -xzf dxvk.tar.gz; \
    DXVK_DIR="/tmp/dxvk-${DXVK_VERSION}"; \
    cp -v "${DXVK_DIR}/x64/d3d11.dll"     "${WINEPREFIX}/drive_c/windows/system32/"; \
    cp -v "${DXVK_DIR}/x64/dxgi.dll"      "${WINEPREFIX}/drive_c/windows/system32/"; \
    cp -v "${DXVK_DIR}/x64/d3d10core.dll" "${WINEPREFIX}/drive_c/windows/system32/" || true; \
    cp -v "${DXVK_DIR}/x32/d3d11.dll"     "${WINEPREFIX}/drive_c/windows/syswow64/"; \
    cp -v "${DXVK_DIR}/x32/dxgi.dll"      "${WINEPREFIX}/drive_c/windows/syswow64/"; \
    cp -v "${DXVK_DIR}/x32/d3d10core.dll" "${WINEPREFIX}/drive_c/windows/syswow64/" || true; \
    rm -rf "/tmp/dxvk-${DXVK_VERSION}" /tmp/dxvk.tar.gz; \
    wineserver -k || true

# NVIDIA branch
FROM app AS nvidia
RUN set -eux; \
    export DISPLAY=:99; \
    Xvfb :99 -screen 0 1024x768x24 -nolisten tcp -noreset & \
    xvfb_pid=$!; \
    trap "kill -TERM $xvfb_pid || true; wait $xvfb_pid || true" EXIT; \
    env WINETRICKS_SUPER_QUIET=1 WINETRICKS_VERBOSE=0 \
      winetricks -q --unattended dxvk; \
    rm -rf /root/.cache/winetricks; \
    wineserver -k || true
