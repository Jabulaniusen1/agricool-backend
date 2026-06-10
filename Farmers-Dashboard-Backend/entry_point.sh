#!/bin/bash
printenv | grep -v "no_proxy" >> /etc/environment

if [ "$#" -gt 0 ]; then
    exec "$@"
fi

exec supervisord -c /scheduler/supervisord.conf
