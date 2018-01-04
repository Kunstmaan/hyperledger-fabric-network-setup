#!/bin/bash
# Created by Guillaume Leurquin, guillaume.leurquin@accenture.com

set -eu -o pipefail

REPO=$1

if [ ! -d "$GOPATH/src/.git" ]; then
  mkdir -p $GOPATH/src
  echo "Cloning repository $REPO..."
  rm -rfd chaincodetmp
  mkdir -p chaincodetmp
  git clone $REPO ./chaincodetmp

  echo "Moving files into $GOPATH/src/ ... "
  mv chaincodetmp/* $GOPATH/src/
  mv chaincodetmp/.[!.]* $GOPATH/src/ # Copy hidden files too

  echo "Removing unused files ... "
  rm -rfd chaincodetmp
fi
pushd $GOPATH/src/
echo "Pulling repository..."
git pull
echo "Done"
popd
