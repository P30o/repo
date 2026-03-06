FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      bash \
      git \
      dpkg \
      xz-utils \
      zstd \
      bzip2 \
      gzip \
      coreutils \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY . /app

CMD ["python", "bot.py"]
