FROM python:3.9-slim

WORKDIR /usr/src/app

COPY requirements.txt .

RUN pip install -r requirements.txt

RUN apt-get update && apt-get install -y \
  ffmpeg \
  audacity \
  yt-dlp \
  && rm -rf /var/lib/apt/lists/*

COPY . .

CMD ["python", "./process.py"]
