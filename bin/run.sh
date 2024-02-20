#!/bin/bash

docker run -it --rm -v "$PWD"/data:/usr/src/app/data -v "$(pwd)":/path/in/container --name my-running-script sermon-processor