#!/bin/bash
# Created by Guillaume Leurquin, guillaume.leurquin@accenture.com

set -eu -o pipefail

if [ $# -ne 6 ];
then
	echo ""
	echo "Usage: "
	echo "	create_peer_env PEER PEER_PORT ORG MSPID ADMIN ORG_FOLDER"
  echo "  Creates a script that changes the environment to the one of the given peer"
	echo ""
	exit 1
fi


PEER=$1
PEER_PORT=$2
ORG=$3
MSPID=$4
ADMIN=$5
ORG_FOLDER=$6

mkdir -p $ORG_FOLDER/../tools
FILE="$ORG_FOLDER/../tools/set_env.$PEER.$ORG.sh"


echo """#!/bin/bash
set -eu -o pipefail

CORE_PEER_MSPCONFIGPATH=/etc/hyperledger/crypto-config/$ORG/users/$ADMIN.$ORG/msp
CORE_PEER_ID=$PEER.$ORG
CORE_PEER_LOCALMSPID=$MSPID
CORE_PEER_ADDRESS=$PEER.$ORG:$PEER_PORT
CORE_PEER_TLS_KEY_FILE=/etc/hyperledger/crypto-config/$ORG/peers/$PEER.$ORG/tlsca/tlsca.$PEER.$ORG-key.pem
CORE_PEER_TLS_CERT_FILE=/etc/hyperledger/crypto-config/$ORG/peers/$PEER.$ORG/tlsca/tlsca.$PEER.$ORG-cert.pem
CORE_PEER_TLS_ROOTCERT_FILE=/etc/hyperledger/crypto-config/$ORG/peers/$PEER.$ORG/tlsca.combined.$PEER.$ORG-cert.pem

export CORE_PEER_MSPCONFIGPATH
export CORE_PEER_ID
export CORE_PEER_LOCALMSPID
export CORE_PEER_ADDRESS
export CORE_PEER_TLS_KEY_FILE
export CORE_PEER_TLS_CERT_FILE
export CORE_PEER_TLS_ROOTCERT_FILE
""" > $FILE

chmod +x $FILE
