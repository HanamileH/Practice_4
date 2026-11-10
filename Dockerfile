FROM python:3.11.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_PORT=8108

WORKDIR /app

COPY config_check.py config.json.example ./

RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app

USER appuser

ENTRYPOINT ["python", "config_check.py"]
CMD ["--config", "config.json.example"]
