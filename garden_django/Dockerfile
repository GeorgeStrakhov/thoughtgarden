# Use the official Python image from the Docker Hub
FROM python:3.11

# Install PostgreSQL client tools
RUN apt-get update && apt-get install -y postgresql-client

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /code

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project and supervisord configurations
COPY . .