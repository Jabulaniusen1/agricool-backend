FROM --platform=linux/amd64 python:3.10-slim

# Set work directory
WORKDIR /app

# COMSOL environment
ENV COMSOL_VERSION=6.3.0.335
ENV COMSOL_CSA_DIR=/media/comsol/csa
ENV COMSOL_PREFS_DIR=/media/comsol/prefs
ENV COMSOL_SETUP_CONFIG=/media/comsol/setupconfig.ini
ENV COMSOL_ROOT=/usr/local/comsol63/runtime
ENV FUSE_PATH=/mnt/comsol

# Add COMSOL runtime to PATH and library paths
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$COMSOL_ROOT/bin/glnxa64
ENV LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$COMSOL_ROOT/lib/glnxa64:$COMSOL_ROOT/ext/graphicsmagick/glnxa64:$COMSOL_ROOT/ext/cadimport/glnxa64

# Base system dependencies (requires BuildKit)
RUN --mount=type=cache,target=/var/cache/apt,id=comsol-dt-apt <<EOF
    apt-get update && apt-get install -y \
        build-essential \
        fuse libfuse2 libfuse-dev \
        pkg-config \
        libswt-gtk-4-jni \
        libsqlite3-dev \
        xvfb xfonts-base x11-xserver-utils dbus-x11 x11-utils \
        gdal-bin libgdal-dev libpq-dev \
        gettext \
        supervisor
EOF

# Set DISPLAY after Xvfb is available
ENV DISPLAY=:0

# Create required directories
RUN mkdir -p /media/comsol/csa /media/comsol/prefs "$FUSE_PATH"

# Add FUSE config
RUN echo "user_allow_other" >> /etc/fuse.conf

# Copy and prepare COMSOL CSA installers
COPY comsol/csa/*.sh /media/comsol/csa/
RUN chmod +x /media/comsol/csa/*.sh

# Create COMSOL setup config
RUN echo -e "installmode = install\nshowgui = 0\nautofinish = 1\nquiet = 0\nagree = 1" > "$COMSOL_SETUP_CONFIG"

# Install COMSOL runtime
RUN --mount=type=tmpfs,target=/tmp \
    for installer in "$COMSOL_CSA_DIR"/*.sh; do \
    bash "$installer" -s "$COMSOL_SETUP_CONFIG" -prefsdir "$COMSOL_PREFS_DIR"; \
    done

# JVM optimizations (optional, guarded)
RUN if [ -d "$COMSOL_ROOT/bin/glnxa64" ]; then \
    INI="$COMSOL_ROOT/bin/glnxa64/comsol.ini"; \
    echo "-Dcs.locale=en_US" >> "$INI" && \
    echo "-Dcs.runtimemode=on" >> "$INI" && \
    echo "-Dcs.runtimeexec=@user.home/.comsol/v63runtime/" >> "$INI" && \
    echo "-XX:+UnlockCommercialFeatures" >> "$INI" && \
    echo "-XX:SharedArchiveFile=$COMSOL_ROOT/comsol.jsa" >> "$INI" && \
    echo "-XX:+UseCompressedOops" >> "$INI" && \
    echo "-XX:+UseCompressedClassPointers" >> "$INI" && \
    echo "-XX:+UseSharedSpaces" >> "$INI" && \
    echo "-XX:+TieredCompilation" >> "$INI" && \
    echo "-XX:TieredStopAtLevel=1" >> "$INI" && \
    echo "-XX:+AggressiveOpts" >> "$INI" && \
    echo "-XX:+UseG1GC" >> "$INI" && \
    echo "-XX:MaxGCPauseMillis=200" >> "$INI" && \
    comsol -XX:DumpLoadedClassList="$COMSOL_ROOT/comsol.1st" && \
    echo "-XX:SharedClassListFile=$COMSOL_ROOT/comsol.1st" >> "$INI" && \
    comsol -XShare:dump && \
    echo "-XShare:on" >> "$INI"; \
    else \
    echo "WARNING: COMSOL runtime not found at $COMSOL_ROOT. Skipping JVM optimizations."; \
    fi

# Copy Python app
COPY Pipfile Pipfile.lock ./
RUN pip install pipenv && pipenv install --deploy --ignore-pipfile

# Copy the application files
COPY ./app /app

# Supervisor configuration
COPY supervisor/supervisord.conf /etc/supervisor/supervisord.conf
RUN mkdir -p /var/run/supervisor /var/log

# Entry script
COPY comsol/comsol_service.sh /usr/sbin/comsol_service.sh
RUN chmod +x /usr/sbin/comsol_service.sh

# Expose port
EXPOSE 5900

# Python output without buffering
ENV PYTHONUNBUFFERED=1

# Start supervisor
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
