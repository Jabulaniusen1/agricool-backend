# FROM Debian Bookworm slim with python 3.9
FROM --platform=linux/amd64 python:3.9-slim

# Set work directory
WORKDIR /app

# Set DISPLAY for Xvfb if needed
ENV DISPLAY=:1

# Install base system dependencies
RUN --mount=type=cache,target=/var/cache/apt <<EOF
  apt-get update && apt-get install -y \
    build-essential \
    libswt-gtk-4-jni \
    xvfb \
    dbus-x11 \
    gdal-bin \
    libgdal-dev \
    libpq-dev \
    gettext
EOF

# Set GDAL environment paths
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal
ENV GDAL_LIBRARY_PATH=/usr/lib/libgdal.so

# Install pipenv
RUN pip install pipenv

# Install dependencies
COPY ./Pipfile ./Pipfile.lock /app/
RUN pipenv install --dev

# Copy app files
COPY ./base /app/base
COPY manage.py /app/manage.py
