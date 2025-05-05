#!/bin/bash

cd /scheduler

# Debug message to check execution
echo "Loading environment variables from /proc/1/environ"

# Read, parse, and export variables using sed and eval
eval $(cat /proc/1/environ | tr '\0' '\n' | sed 's/^\([^=]*\)=\(.*\)$/export \1="\2"/')

# Print environment variables to verify they are loaded
echo "Environment variables after loading:"
printenv