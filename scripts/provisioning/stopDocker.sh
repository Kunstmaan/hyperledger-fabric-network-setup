#!/bin/bash

# Exits all running docker containers

# Exit immediately if a pipeline returns non-zero status.
# Result of pipeline is the last command
# Unset variables are considered an error
set -eu -o pipefail

# Remove interraction
export DEBIAN_FRONTEND=noninteractive

function dkcl(){
  if command -v docker > /dev/null 2>&1; then {
    CONTAINER_IDS=$(docker ps -aq)
    echo
    if [ -z "$CONTAINER_IDS" ] || [ "$CONTAINER_IDS" = " " ]; then
      echo "========== No containers available for deletion =========="
    else
      docker rm -f $CONTAINER_IDS
    fi
    echo
  }; fi
}

dkcl
