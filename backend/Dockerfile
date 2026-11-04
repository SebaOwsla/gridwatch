FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
COPY backend /srv/backend
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir /srv/backend \
    && useradd --create-home --uid 10001 gridwatch

USER gridwatch
WORKDIR /srv/backend
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
