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

RUN useradd --create-home app && chown -R app /app
USER app

EXPOSE 8000

# The host sets PORT; migrations run before the server starts
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120"]
