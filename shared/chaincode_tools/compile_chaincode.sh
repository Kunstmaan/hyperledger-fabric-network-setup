#!/bin/bash
# Created by Guillaume Leurquin, guillaume.leurquin@accenture.com

set -eu -o pipefail

puts() {
  local GREEN='\033[0;32m'
  local NC='\033[0m'
  echo -e "${GREEN}$*${NC}"
}

if [ $# -ne 1 ];
then
  echo ""
  echo "Usage: "
  echo "	compile_chaincode chaincode_path"
  echo ""
  exit 1
fi

chaincode_path=$1
puts "Compiling chaincode..."

pushd $GOPATH/src/$chaincode_path > /dev/null
puts "==> Getting shim package from hyperledger fabric..."
go get -u --tags nopkcs11 github.com/hyperledger/fabric/core/chaincode/shim
puts "==> Compiling..."
go build --tags nopkcs11
popd > /dev/null

puts "Done. Chaincode $chaincode_path compiled !"
