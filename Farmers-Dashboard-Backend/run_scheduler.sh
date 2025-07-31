#!/bin/sh

cd /scheduler

# Export environment variables as inherited from the docker container
eval $(cat /proc/1/environ | tr '\0' '\n' | sed 's/^\([^=]*\)=\(.*\)$/export \1="\2"/')

# Run the Python script to update the company_metrics and cooling_unit_metrics tables
/usr/local/bin/python3 /scheduler/indicator_reporter.py
