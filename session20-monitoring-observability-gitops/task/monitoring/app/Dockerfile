FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
USER 10001
EXPOSE 8000
# python:3.12-slim has no curl, so the health check uses the standard library
HEALTHCHECK --interval=5s --timeout=2s --retries=2 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"
CMD ["python", "-u", "app.py"]
