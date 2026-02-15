# Sparse Cosine Optimized Policy Evolution for Playing Dark Souls: Remastered

This repository has the development of the integration of SCOPE into the Dark Souls game.

For the game setup to work, you need the source code of Dark Souls Remastered inside a zip file titled `Dark.Souls.Remastered.v1.04.zip`.

## Setup

The container for running the game can be built using the docker-compose file
```bash
docker compose build  # Build the container
```

Before running the container, allow the root user to access your X server and get the game source from your Drive folder
```bash
xhost +si:localuser:root
./get_game.sh "drive-link"
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

## Running the Game

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

## Running the Training
