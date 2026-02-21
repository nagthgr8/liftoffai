# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.10.12
FROM python:${PYTHON_VERSION}-slim

LABEL fly_launch_runtime="flask"

WORKDIR /code

# Install dependencies
COPY requirements.txt requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Expose the internal port Fly expects
EXPOSE 8080

# Use Gunicorn for production (1 worker is fine for free tier)
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080", "--workers", "1"]
