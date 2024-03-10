FROM python:3.9-slim

WORKDIR /usr/src/app

COPY requirements.txt .

RUN apt-get update && apt-get install -y \
  ffmpeg \
  audacity \
  yt-dlp \
  git \
  && rm -rf /var/lib/apt/lists/*

RUN pip install -r requirements.txt

COPY . .

CMD ["python", "./process.py"]
