# Backend image (mock-first). No `ml` extra: MediaPipe is heavy and the mock
# provider doesn't need real landmarks. For real server-side face detection,
# install the `ml` extra + model bundle (see scripts/phase0/README.md).
FROM python:3.11-slim

WORKDIR /app

COPY . .
RUN pip install --no-cache-dir -e "."

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
