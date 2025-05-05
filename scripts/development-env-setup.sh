#!/bin/bash

# Runtime helpers
CURRENT_DIR=$(dirname -- "$0")
MAIN_API_ROOT=$(realpath "$CURRENT_DIR/..")
VENV=$(pipenv --venv)
VENVS_DIR=$(dirname $VENV)

# Setup pyrightconfig.json
cat <<EOF > $MAIN_API_ROOT/pyrightconfig.json
{
  "venvPath": "$VENVS_DIR",
  "venv": "$VENV"
}
EOF
