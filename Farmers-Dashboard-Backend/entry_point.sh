#!/bin/bash
printenv | grep -v "no_proxy" >> /etc/environment
exec supervisord -c /scheduler/supervisord.conf
