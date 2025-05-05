#!/bin/sh

# Polyfill APP_DATA
if [ ! -d $APP_DATA ]; then
    mkdir -p $APP_DATA;
fi;

# fill the files that do not exist
rsync --quiet --recursive --update "$APP_DEFAULT_DATA" "$APP_DATA";

exec $@;
