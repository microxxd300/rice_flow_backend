FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Commit the image was built from; /api/health/ reports it so CD can confirm the release
ARG GIT_SHA=dev
ENV GIT_SHA=${GIT_SHA}

# Strip Windows line endings in case the repo was checked out with CRLF
RUN sed -i 's/\r$//' docker/entrypoint.sh \
    && useradd --create-home app \
    && chown -R app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD ["python", "docker/healthcheck.py"]

# Runs migrate and collectstatic, then gunicorn (the host may set PORT)
CMD ["sh", "docker/entrypoint.sh"]
