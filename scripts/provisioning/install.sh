#!/bin/bash
# Created by Guillaume Leurquin, guillaume.leurquin@accenture.com

# Designed to run on an AWS node, to install missing packages for hyperledger.
# Not used anymore. You can use this manually if you wish.

# Exit immediately if a pipeline returns non-zero status.
# Result of pipeline is the last command
# Unset variables are considered an error
set -euv -o pipefail

HL_VERSION=$1


# Remove interraction
export DEBIAN_FRONTEND=noninteractive

puts() {
  local GREEN='\033[0;32m'
  local NC='\033[0m'
  echo -e "${GREEN}$*${NC}"
}

updatePath() {
  # NOTE Sourcing profile does not work during provisionning
  puts "Adding $1 to PATH"
  echo "$PATH"|grep -q "$1" || { echo "PATH=\$PATH:$1" >> /home/ubuntu/.profile; }
  export PATH=$PATH:$1
}

updateProfile() {
  if [ $# -ne 2 ]; then
    echo "updateProfile requires 2 arguments: VAR and VAL"
    exit 1
  fi
  # NOTE Sourcing profile does not work during provisionning
  puts "Exporting $1=$2"
  grep -q "export $1=$2" < /home/ubuntu/.profile  || { echo "export $1=$2" >> /home/ubuntu/.profile; }
  export "$1"="$2"
}

puts "Enabling colors for the shell"
sed -i -e 's/#force_color_prompt=yes/force_color_prompt=yes/' ~/.bashrc

grep -q "alias up=\"cd ..\"" < /home/ubuntu/.profile  || { echo "alias up=\"cd ..\"" >> /home/ubuntu/.profile; } # Convenience up command

puts "Installing libtool and libltdl-dev..."
apt-get install -y libtool libltdl-dev
puts "Done."

# Install git
if command -v git > /dev/null 2>&1; then puts "Git is already installed. Skipping..."; else {
  puts "Installing Git..."
  apt-get install git
  puts "Done."
}; fi

# Install Node
if command -v node > /dev/null 2>&1; then puts "Nodejs is already installed. Skipping..."; else {
  puts "Installing Node..."
  curl -sL https://deb.nodesource.com/setup_6.x | sudo -E bash -
  apt-get install -y nodejs build-essential
  puts "Done."
}; fi

# Install Go
if command -v go > /dev/null 2>&1; then puts "Go is already installed. Skipping..."; else {
  puts "Installing Go..."
  GOREL=go1.7.4.linux-amd64.tar.gz
  wget -q https://storage.googleapis.com/golang/$GOREL
  tar xfz $GOREL
  rm -rf /usr/local/go
  mv go /usr/local/go
  rm -f $GOREL
  updateProfile GOROOT /usr/local/go
  mkdir ~/go > /dev/null 2>&1
  updateProfile GOPATH /home/ubuntu/go
  updatePath "\$GOROOT/bin"
  puts "Done."
}; fi

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
  puts "Installing Hyperledger and pulling Docker images..."
  HLPATH=/usr/local/hyperledger
  rm -rf $HLPATH
  mkdir $HLPATH
  pushd $HLPATH > /dev/null
  curl -sSL https://raw.githubusercontent.com/hyperledger/fabric/master/scripts/bootstrap-$HL_VERSION.sh | bash
  popd > /dev/null
  updatePath $HLPATH/bin
  puts "Done."
}; fi

if command -v docker-compose > /dev/null 2>&1; then puts "Docker-compose is already installed. Skipping..."; else {
  puts "Installing Docker-compose..."
  apt-get install -y docker-compose
  puts "Done."
}; fi

puts "Installing go dependencies for fabric..."
export GOPATH=/home/ubuntu/go
/usr/local/go/bin/go get -u --tags nopkcs11 github.com/hyperledger/fabric/core/chaincode/shim
puts "Done."
