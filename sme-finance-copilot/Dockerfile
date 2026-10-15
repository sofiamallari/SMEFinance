FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd -m appuser && mkdir -p logs && chown -R appuser /app
RUN chmod 0755 /app/docker-entrypoint.sh
ENV HOST=0.0.0.0 PORT=8000 PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
EXPOSE 8000
HEALTHCHECK CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/login',timeout=5)"
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "-m", "copilot.server"]
