FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
COPY simulator /srv/simulator
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir /srv/simulator \
    && useradd --create-home --uid 10002 simulator

USER simulator
CMD ["python", "-m", "gridwatch_simulator"]
