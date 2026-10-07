FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
# Install the app's dependencies, then remove pip itself. Nothing needs pip at
# runtime, and Trivy found HIGH CVEs in the libraries pip vendors (urllib3,
# msgpack, setuptools/pkg_resources) - code the app never uses but ships anyway.
RUN pip install --no-cache-dir -r requirements.txt \
 && pip uninstall -y pip

COPY app ./app

# Numeric UID, not a name: Kubernetes' runAsNonRoot can only verify a number.
RUN useradd --create-home --uid 10001 appuser
USER 10001

EXPOSE 5001

# gunicorn, not `python app/app.py`: the Flask development server is not meant
# for production, and the as-shipped version ran it with the debugger enabled.
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "2", "--access-logfile", "-", "app.app:app"]
