# syntax=docker/dockerfile:1

FROM us-docker.pkg.dev/ce-builder/docker/builder-python:ubuntu2204 as builder

# Install requirements for building wheels if not included in builder-python
#RUN apt-get update && \
#    apt-get install -y \
#        build-essential \
#        libpq-dev \
#    && rm -rf /var/lib/apt/lists/*

# Build Python packages from requirements.txt and from the project directory
RUN mkdir -p /app
COPY . /app
RUN --mount=type=secret,id=AR_ACCESS_TOKEN pip wheel \
    --extra-index-url https://oauth2accesstoken:$(</run/secrets/AR_ACCESS_TOKEN)@us-python.pkg.dev/ce-builder/python/simple \
    --no-cache-dir --default-timeout=100 --wheel-dir=/wheels \
    -r /app/requirements.txt \
    /app

FROM us-docker.pkg.dev/ce-builder/docker/base-python:ubuntu2204

# If gdal is needed for your project, use python-gdal as the base image
#FROM us-docker.pkg.dev/ce-builder/docker/python-gdal:ubuntu2204

# Install the packages using the wheel files and remove them in the same RUN command
RUN --mount=type=bind,from=builder,source=/wheels,target=/wheels \
    pip install --no-deps --no-cache-dir /wheels/*

ENTRYPOINT ["py-spfi-api"]
