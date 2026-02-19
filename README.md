# Sparse Cosine Optimized Policy Evolution for Playing Dark Souls: Remastered

This repository has the development of the integration of SCOPE into the Dark Souls game.

## Setup

Before following the container setup, you need to get the game source code inside a zip file titled `Dark.Souls.Remastered.v1.04.zip`.
The `get_game.sh` script will help you to get the game source code from your Google Drive folder.
```bash
./get_game.sh "drive-link-to-the-game-zip-file"
```

The container for running the game can be built using the docker-compose file
```bash
docker compose build
```

Before running the container, allow the root user to access your X server
```bash
xhost +si:localuser:root
```

### Running the container in an Nvidia GPU machine

Run the container using the docker-compose file
```bash
docker compose run --rm dsr-nvidia
```

If you want to connect a frame into the headless mode, expose a specific port to the container
```bash
docker compose run --rm -p 127.0.0.1:5900:5900 dsr-nvidia
```

> The current setup only supports running the container with a machine with Nvidia GPU.
>
> Any device with an integrated GPU or AMD GPU is not supported.

## Running the Game Inside the Container

### Directly running inside a GUI
```bash
./scripts/run_game.sh gui
```

### Running completely headless
```bash
./scripts/run_game.sh headless
```

### Running headless with an attached virtual display
```bash
./scripts/run_game.sh headless-vnc
```
```bash
vncviewer 127.0.0.1:5900  # Run this in your host machine to connect to the display
```
