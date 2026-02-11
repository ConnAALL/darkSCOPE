FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# --- Base deps + 32-bit support ---
RUN dpkg --add-architecture i386 && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
      ca-certificates curl gnupg2 wget \
      unzip cabextract xz-utils p7zip-full file \
      bash vim git \
      procps psmisc \
      x11-utils x11-xserver-utils xauth \
      zenity \
      vulkan-tools \
      libvulkan1 libvulkan1:i386 \
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
      winbind \
      fonts-wine \
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
    rm -rf /var/lib/apt/lists/*

# --- Winetricks: use latest upstream script (avoid ancient distro version) ---
RUN wget -O /usr/local/bin/winetricks \
      https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks && \
    chmod +x /usr/local/bin/winetricks

# --- Wine defaults (override at runtime if you want ephemeral) ---
ENV WINEPREFIX=/opt/prefix
ENV WINEARCH=win64
ENV WINEDEBUG=-all
ENV WINEESYNC=0
ENV WINEFSYNC=0
ENV WINEDLLOVERRIDES="mscoree,mshtml=;winemenubuilder.exe=d"
ENV WINETRICKS_OPT_UNATTENDED=1

# --- Game ---
COPY Dark.Souls.Remastered.v1.04.zip /opt/game/game.zip
RUN mkdir -p /opt/game && \
    7z x -y -o/opt/game /opt/game/game.zip && \
    rm -f /opt/game/game.zip

# --- Script ---
COPY run_gui.sh /usr/local/bin/run_gui.sh
RUN chmod +x /usr/local/bin/run_gui.sh

WORKDIR /root
CMD ["/bin/bash"]
