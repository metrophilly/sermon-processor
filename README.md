# 🎛️ Metro Sermons Processor

This is a small script to automate the downloading, processing, and scrubbing of
Metro's weekly sermons from YouTube and audio of Spotify. This guide will walk
you through setting up `sermon-processor` project using Docker.

## Prerequisites

Ensure you have `docker` and `docker-compose` installed on your system. You can
check if they're installed by running:

```bash
docker --version
docker-compose --version
```

## Set config parameters

The `.env` file allows for pre-filled parameters. If you don't have it, run the
following command to use the provided template. Please reference the Bitwarden
Vault for keys

```bash
cp .env.example .env
```

Ensure that you have the `url`, `start`, and `end` params set to run the script.

## Run the script

1. Ensure that you have Docker Desktop running in the background.

2. Then run the startup script in the `/bin` directory. Run the following to
   start:

```bash
sh bin/start.sh
```

Follow the prompts to either run the `[a]udio` or `[v]ideo` scripts.

- If you're having trouble running the script, make sure the file has the
  correct executable permissions by running:

  ```bash
  chmod +x bin/start.sh
  ```

## Post-Processing

To ensure the correct media file is generated each week, it is essential to
delete the `tmp` directory after the current media file has been successfully
created. If the `tmp` directory is not deleted, next week’s media file will use
the previous week’s data instead of generating a new file.

Delete the `tmp` directory by either:

- Manually deleting the folder
- Running the command `rm -r tmp` in your terminal

Once the automated processing is complete, the final media file will be saved to
`data/` by default, or the specified data directory on your host machine.
Afterwards, follow the manual steps that print in the console.

## Deactivating Docker Container

When you're done, the Docker container will automatically stop as we've used the
`--rm` flag, which removes the container after it exits. If you'd like to
manually stop the image, you can run the following:

```bash
docker-compose down
```
