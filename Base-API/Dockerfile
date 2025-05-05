# FROM Debian Bookworm slim with python 3.9
FROM --platform=linux/amd64 python:3.9-slim

# NOTE: JDK is not necessary as COMSOL already includes their own.
ENV DISPLAY=:1
RUN --mount=type=cache,target=/var/cache/apt <<EOF
  apt-get update && apt-get install -y build-essential libswt-gtk-4-jni xvfb dbus-x11 gdal-bin libgdal-dev libpq-dev gettext
EOF

# Set GDAL environment paths
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal
ENV GDAL_LIBRARY_PATH=/usr/lib/libgdal.so

# Set work directory
WORKDIR /app

# Install COMSOL Standalone Application
COPY comsol/csa/*.sh /media/comsol/csa/

# Install the runtime of all the .sh files
ENV COMSOL_CSA_DIR=/media/comsol/csa/
ENV COMSOL_PREFS_DIR=/media/comsol/prefs/
ENV COMSOL_SETUP_CONFIG=/media/comsol/setupconfig.ini
RUN echo "installmode = install\nshowgui = 0\nautofinish = 1\nquiet = 0\nagree = 1" > $COMSOL_SETUP_CONFIG
RUN <<EOF
for csa in `ls $COMSOL_CSA_DIR`; do
  "$COMSOL_CSA_DIR/$csa" -s "$COMSOL_SETUP_CONFIG" -prefsdir "$COMSOL_PREFS_DIR";
done
EOF

# The CSA files install the COMSOL runtime, we're just gonna change the ini files to introduce optimizations
ENV COMSOL_VERSION=6.0.0.354
ENV COMSOL_ROOT=/usr/local/comsol60/runtime/$COMSOL_VERSION
ENV PATH=$PATH:$COMSOL_ROOT/bin/glnxa64
ENV LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$COMSOL_ROOT/lib/glnxa64:$COMSOL_ROOT/ext/graphicsmagick/glnxa64:$COMSOL_ROOT/ext/cadimport/glnxa64

# COMSOL runtime jdk optimizations
RUN echo "-Dcs.locale=en_US" >> $COMSOL_ROOT/bin/glnxa64/comsol.ini
RUN echo "-Dcs.runtimemode=on" >> $COMSOL_ROOT/bin/glnxa64/comsol.ini
RUN echo "-Dcs.runtimeexec=@user.home/.comsol/v60runtime/" >> $COMSOL_ROOT/bin/glnxa64/comsol.ini
RUN echo "-XX:+UnlockCommercialFeatures" >> $COMSOL_ROOT/bin/glnxa64/comsol.ini
RUN echo "-XX:SharedArchiveFile=$COMSOL_ROOT/comsol.jsa" >> $COMSOL_ROOT/bin/glnxa64/comsol.ini
RUN echo "-XX:+UseCompressedOops" >> $COMSOL_ROOT/bin/glnxa64/comsol.ini
RUN echo "-XX:+UseCompressedClassPointers" >> $COMSOL_ROOT/bin/glnxa64/comsol.ini
RUN echo "-XX:+UseSharedSpaces" >> $COMSOL_ROOT/bin/glnxa64/comsol.ini
RUN echo "-XX:+TieredCompilation" >> $COMSOL_ROOT/bin/glnxa64/comsol.ini
RUN echo "-XX:TieredStopAtLevel=1" >> $COMSOL_ROOT/bin/glnxa64/comsol.ini
RUN echo "-XX:+AggressiveOpts" >> $COMSOL_ROOT/bin/glnxa64/comsol.ini
RUN echo "-XX:+UseG1GC" >> $COMSOL_ROOT/bin/glnxa64/comsol.ini
RUN echo "-XX:MaxGCPauseMillis=200" >> $COMSOL_ROOT/bin/glnxa64/comsol.ini
RUN comsol -XX:DumpLoadedClassList=$COMSOL_ROOT/comsol.1st
RUN echo "-XX:SharedClassListFile=$COMSOL_ROOT/comsol.1st" >> $COMSOL_ROOT/bin/glnxa64/comsol.ini
RUN comsol -XShare:dump # Class Data Sharing
RUN echo "-XShare:on" >> $COMSOL_ROOT/bin/glnxa64/comsol.ini

# Install pipenv
RUN pip install pipenv

# Install dependencies
COPY ./Pip* /app/
RUN pipenv install --dev

COPY ./base /app/base
COPY manage.py /app/manage.py
