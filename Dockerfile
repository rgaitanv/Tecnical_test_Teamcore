# Use an official Airflow image as a parent image.
# Using a specific version is highly recommended for production environments.
ARG AIRFLOW_VERSION=2.8.1
FROM apache/airflow:${AIRFLOW_VERSION}

ENV PIP_NO_CACHE_DIR=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DOCKER_BUILDKIT=1
# Set the Airflow home directory
ENV AIRFLOW_USER_HOME /opt/airflow

# Switch to the root user to create directories and set permissions
USER root

# Create the app directory inside the container.
# While volumes handle the mapping, this ensures the directory exists with proper ownership.
RUN mkdir -p /opt/airflow/app && chown -R airflow:0 /opt/airflow/app

# Switch back to the non-privileged airflow user
USER airflow

# Install Python dependencies
# Copy only the requirements file to leverage Docker's layer cache.
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt