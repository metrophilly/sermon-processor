# 🎛️ Metro Sermons Processor

This is a small script to automate the downloading, processing, and scrubbing of
Metro's weekly sermons from YouTube. This guide will walk you through setting up
the sermon-processor project using Docker.

## Prerequisites

Ensure you have Docker installed on your system. You can check if Docker is
installed by running:

```bash
docker --version
```

## Build Docker Image

Docker simplifies the setup process by containerizing the environment and
dependencies. Follow these steps to build the docker image.

```bash
docker build -t sermon-processor .
```

## Run the Script

Start the sermon-processor in a Docker container. (Optional: Replace `$PWD` with
the path where you want to store processed audio files on your host machine.)

```bash
docker run -it --rm -v "$PWD"/data:/usr/src/app/data -v "$(pwd)":/path/in/container --name my-running-script sermon-processor
```

Follow the prompts to input the YouTube URL and timestamps for audio processing.

## Post-Processing

Once the automated processing is complete, the final audio file will be saved to
`./data/` by default, or the specified data directory on your host machine.
Afterwards, follow the manual steps that print in the console.

## Deactivating Docker Container

When you're done, the Docker container will automatically stop as we've used the
`--rm` flag, which removes the container after it exits.
