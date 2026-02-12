# Sparse Cosine Optimized Policy Evolution for Playing Dark Souls: Remastered

This repository has the development of the integration of SCOPE into the Dark Souls game.

For the game setup to work, you need the source code of Dark Souls Remastered inside a zip file titled `Dark.Souls.Remastered.v1.04.zip`.

To build the docker container that hosts the game, run
```
docker build -t dsr-wine:latest .
```

To start the container, run
```
docker run -it --gpus all --cap-add=SYS_PTRACE --security-opt seccomp=unconfined --security-opt apparmor=unconfined -e DISPLAY="$DISPLAY" -v /tmp/.X11-unix:/tmp/.X11-unix dsr-wine:latest /bin/bash
```