FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg espeak-ng fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY renderer.py /app/renderer.py
ENV PYTHONUNBUFFERED=1
RUN VCI_BUILD_SMOKE_TEST=1 python /app/renderer.py
CMD ["python","/app/renderer.py"]
