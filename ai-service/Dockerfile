FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app/ai-service
COPY ai-service/requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt && useradd --uid 10001 --create-home appuser
COPY ai-service/app ./app
COPY docs/source-profile.json /app/docs/source-profile.json
COPY evaluation /app/evaluation
RUN mkdir -p /app/data/uploads /app/data/generated && chown -R appuser:appuser /app/data
USER appuser
EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--workers","1","--limit-concurrency","32","--no-access-log"]
