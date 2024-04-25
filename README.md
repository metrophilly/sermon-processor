# 🎛️ Metro Sermons Processor

This is a small script to automate the downloading, processing, and scrubbing of
Metro's weekly sermons from YouTube. This guide will walk you through setting up
the sermon-processor project using Docker.

## Prerequisites

Ensure you have `Docker` and `docker-compose` installed on your system. You can
check if they're installed by running:

```bash
docker --version
docker-compose --version
```

## Set config parameters

The file `config.txt` allows for pre-filled parameters. If you don't have it,
run the following command to use the provided template.

```bash
cp config/config.example.txt config/config.txt
```

Ensure that you have the following params set to run the script:

- For audio:
  - url, start, and end time
- For video:
  - (for now) the 'base' video set to `config/base.mp4`
  - the intro and outro urls should be consistent

## Build Docker Image

Docker-compose simplifies the setup process by containerizing the environment
and dependencies. Follow these steps to build the docker image.

```bash
docker-compose build
```

## Run the script

Now run the `sermon-processor` image we just built. (Usually we could run `up`,
but we need to use `run` because we need to interact with the script to add the
url and timestamp inputs.)

```bash
docker-compose run sermon-processor
```

Follow the prompts to either run the `[a]udio` or `[v]ideo` scripts.

## Post-Processing

#### Audio

Once the automated processing is complete, the final audio file will be saved to
`./data/` by default, or the specified data directory on your host machine.
Afterwards, follow the manual steps that print in the console.

#### Video

The final video will be saved as `./data/FINAL_full-compressed.mp4` by default.

## Deactivating Docker Container

When you're done, the Docker container will automatically stop as we've used the
`--rm` flag, which removes the container after it exits. If you'd like to
manually stop the image, you can run the following:

```bash
docker-compose down
```
