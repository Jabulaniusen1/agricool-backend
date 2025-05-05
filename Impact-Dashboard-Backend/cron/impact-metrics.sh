#!/bin/bash

cd /scheduler

# Export environment variables as inherited from the docker container
eval $(cat /proc/1/environ | tr '\0' '\n' | sed 's/^\([^=]*\)=\(.*\)$/export \1="\2"/')

python3 /scheduler/indicator_reporter.py --view impact_metrics;
