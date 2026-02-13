FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Enable the 32-bit packages
RUN dpkg --add-architecture i386

# Installing the base dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl gnupg2 wget \
      unzip cabextract xz-utils p7zip-full file \
      bash git vim htop procps psmisc \
      x11-utils x11-xserver-utils xauth \
      vulkan-tools \
      pulseaudio pulseaudio-utils \
      xvfb \
      winbind \
      fonts-wine \
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
      libpulse0 libpulse0:i386 \
    && rm -rf /var/lib/apt/lists/*

# Installing WineHQ repo (Jammy) and Wine stable
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://dl.winehq.org/wine-builds/winehq.key | \
      gpg --dearmor -o /etc/apt/keyrings/winehq-archive.key && \
    curl -fsSL https://dl.winehq.org/wine-builds/ubuntu/dists/jammy/winehq-jammy.sources | \
      sed 's#Signed-By:.*#Signed-By: /etc/apt/keyrings/winehq-archive.key#' \
      > /etc/apt/sources.list.d/winehq-jammy.sources && \
    apt-get update && \
    apt-get install -y --install-recommends winehq-stable && \
    rm -rf /var/lib/apt/lists/*

# Installing Winetricks (latest upstream script)
RUN wget -qO /usr/local/bin/winetricks \
      https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks && \
    chmod +x /usr/local/bin/winetricks

# Setting the default values
ENV WINEPREFIX=/opt/prefix \
    WINEARCH=win64 \
    WINEDEBUG=-all \
    GAME_ROOT=/root/Dark.Souls.Remastered.v1.04 \
    WINEESYNC=0 \
    WINEFSYNC=0 \
    WINEDLLOVERRIDES="mscoree,mshtml=;winemenubuilder.exe=d" \
    WINETRICKS_OPT_UNATTENDED=1

# Preparing the persistent Wine prefix in headless mode
RUN mkdir -p "$WINEPREFIX" && \
    xvfb-run -a wineboot --init && \
    xvfb-run -a env WINETRICKS_SUPER_QUIET=1 WINETRICKS_VERBOSE=0 \
      winetricks -q --unattended win10 vcrun2022 d3dcompiler_47 dxvk && \
    rm -rf /root/.cache/winetricks

WORKDIR /root

# Copy the entire current project directory into /root
COPY scripts /root/scripts
COPY darkAgent /root/darkAgent
COPY Dark.Souls.Remastered.v1.04.zip /root/Dark.Souls.Remastered.v1.04.zip

# Unzip the game files into the root directory
RUN 7z x -y -o/root /root/Dark.Souls.Remastered.v1.04.zip && rm -f /root/Dark.Souls.Remastered.v1.04.zip

RUN chmod +x /root/scripts/entrypoint.sh
RUN chmod +x /root/scripts/run_headless.sh
RUN chmod +x /root/scripts/run_gui.sh

# When the container is started, the entrypoint script will be executed
ENTRYPOINT ["/root/scripts/entrypoint.sh"]
CMD ["/bin/bash"]
