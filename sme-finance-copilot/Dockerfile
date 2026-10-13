FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN useradd -m appuser && mkdir -p logs && chown -R appuser /app
USER appuser
ENV HOST=0.0.0.0 PORT=8000 PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/health')"
CMD ["python", "-m", "copilot.server"]
