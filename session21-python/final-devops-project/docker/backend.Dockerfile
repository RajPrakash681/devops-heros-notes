# Build context: application/backend   (docker build -f docker/backend.Dockerfile application/backend)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
# Install runtime deps, then remove pip itself: nothing needs it at runtime and Trivy
# reports CVEs in the libraries pip vendors (lesson from session 17).
RUN pip install --no-cache-dir -r requirements.txt \
 && pip uninstall -y pip \
 && useradd --create-home --uid 10001 appuser

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

ARG GIT_SHA=dev
ENV GIT_SHA=${GIT_SHA}
LABEL org.opencontainers.image.source="https://github.com/RajPrakash681/devops-heros-notes" \
      org.opencontainers.image.revision="${GIT_SHA}"

# Numeric UID so Kubernetes runAsNonRoot can verify it.
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]
# Migrations are a separate step (init container / compose `migrate` service).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
