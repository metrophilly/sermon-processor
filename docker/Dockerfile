FROM python:3.9-slim AS base

WORKDIR /usr/src/app

COPY requirements.txt .

RUN apt-get update && apt-get install -y \
  ffmpeg \
  git \
  && rm -rf /var/lib/apt/lists/*

RUN pip install -r requirements.txt

COPY . .

ENV PYTHONPATH="/usr/src/app"

# Test stage
FROM base AS test
RUN pip install pytest pytest-mock pydub
CMD ["pytest", "tests/"]

# Production stage
FROM base AS production
CMD ["python3", "startup.py"]
