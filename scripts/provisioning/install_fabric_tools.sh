#!/bin/bash
# Created by Guillaume Leurquin, guillaume.leurquin@accenture.com

# Installs configtxgen, configtxlator, cryptogen, orderer and peer

# Exit immediately if a pipeline returns non-zero status.
# Result of pipeline is the last command
# Unset variables are considered an error
set -eu -o pipefail

# Remove interraction
export DEBIAN_FRONTEND=noninteractive

puts() {
  local GREEN='\033[0;32m'
  local NC='\033[0m'
  echo -e "${GREEN}$*${NC}"
}

export VERSION=1.0.3
ARCH=$(echo "$(uname -s|tr '[:upper:]' '[:lower:]'|sed 's/mingw64_nt.*/windows/')-$(uname -m | sed 's/x86_64/amd64/g')" | awk '{print tolower($0)}')
export ARCH
#Set MARCH variable i.e ppc64le,s390x,x86_64,i386

updatePath() {
  # NOTE Sourcing profile does not work during provisionning
  puts "Adding $1 to PATH"
  echo "$PATH"|grep -q "$1" || { echo "PATH=\$PATH:$1" >> $HOME/.profile; }
  export PATH=$PATH:$1
}

hlisinstalled() {
  # Test for hyperledger installation
  a="command -v configtxgen > /dev/null 2>&1"
  b="command -v configtxlator > /dev/null 2>&1"
  c="command -v cryptogen > /dev/null 2>&1"
  d="command -v orderer > /dev/null 2>&1"
  e="command -v peer > /dev/null 2>&1"
  $a && $b && $c && $d && $e
}

# Install hyperledger binaries
if hlisinstalled > /dev/null 2>&1; then puts "Hyperledger is already installed. Skipping..."; else {
  puts "Installing Hyperledger"
  HLPATH=/usr/local/hyperledger
  rm -rf $HLPATH
  mkdir $HLPATH
  pushd $HLPATH > /dev/null
  echo "===> Downloading platform binaries"
  curl -k https://nexus.hyperledger.org/content/repositories/releases/org/hyperledger/fabric/hyperledger-fabric/${ARCH}-${VERSION}/hyperledger-fabric-${ARCH}-${VERSION}.tar.gz | tar xz
  popd > /dev/null
  updatePath $HLPATH/bin
  puts "Done."
}; fi
