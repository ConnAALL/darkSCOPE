FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# --- Base deps + 32-bit support ---
RUN dpkg --add-architecture i386 && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
      ca-certificates curl gnupg2 \
      unzip cabextract xz-utils p7zip-full \
      python3 python3-pip \
      xvfb x11-utils \
      xauth \
      bash git btop \
      vulkan-tools \
      libvulkan1 libvulkan1:i386 \
      libgl1 libgl1:i386 \
      libglib2.0-0 \
      winbind \
    && rm -rf /var/lib/apt/lists/*

# --- WineHQ repo (Jammy) + Wine stable ---
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://dl.winehq.org/wine-builds/winehq.key | \
      gpg --dearmor -o /etc/apt/keyrings/winehq-archive.key && \
    curl -fsSL https://dl.winehq.org/wine-builds/ubuntu/dists/jammy/winehq-jammy.sources | \
      sed 's#Signed-By:.*#Signed-By: /etc/apt/keyrings/winehq-archive.key#' \
      > /etc/apt/sources.list.d/winehq-jammy.sources && \
    apt-get update && \
    apt-get install -y --install-recommends winehq-stable && \
    apt-get install -y --no-install-recommends winetricks && \
    rm -rf /var/lib/apt/lists/*

# --- Wine defaults ---
ENV WINEPREFIX=/opt/prefix
ENV WINEDEBUG=-all
ENV WINEESYNC=0
ENV WINEFSYNC=0
ENV WINEDLLOVERRIDES="mscoree,mshtml=;winemenubuilder.exe=d"
ENV WINETRICKS_OPT_UNATTENDED=1
ENV WINETRICKS_SUPER_QUIET=1

# --- Unpack game zip from local build context into /opt/game ---
# Put your already-downloaded zip next to this Dockerfile named: game.zip
COPY Dark.Souls.Remastered.v1.04.zip /opt/game/game.zip
RUN 7z x -y -o/opt/game /opt/game/game.zip && rm -f /opt/game/game.zip

# --- Runtime 3D + audio libs (kept separate to preserve game download cache) ---
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      mesa-utils \
      libgl1-mesa-dri libgl1-mesa-dri:i386 \
      mesa-vulkan-drivers mesa-vulkan-drivers:i386 \
      libasound2 libasound2:i386 \
    && rm -rf /var/lib/apt/lists/*

# --- Scripts ---
COPY run_gui.sh /usr/local/bin/run_gui.sh
COPY run_headless.sh /usr/local/bin/run_headless.sh
RUN chmod +x /usr/local/bin/run_gui.sh /usr/local/bin/run_headless.sh

WORKDIR /root
CMD ["/bin/bash"]
