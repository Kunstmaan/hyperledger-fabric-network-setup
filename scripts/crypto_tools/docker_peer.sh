#!/bin/bash
# Created by Guillaume Leurquin, guillaume.leurquin@accenture.com

set -eu -o pipefail

if [ $# -ne 4 ];
then
  echo ""
  echo "Usage: "
  echo "  docker_peer COMMON_NAME ORGANISATION PORTS COUCHDBPORT"
  echo "  PORTS are comma separated of the form HOSTPORT:CONTAINERPORT"
  echo "  This script creates a docker file to be able to run a hyperledger"
  echo "  fabric peer"
  echo ""
  exit 1
fi

CN=$1
ORG=$2
PORTS=$(echo $3 | tr "," " ") # comma separated peers
COUCHDBPORT=$4
declare -a PORTS="( $PORTS )"
FOLDER=$GEN_PATH/docker
mkdir -p "$FOLDER"
FILE="$FOLDER/$CN.$ORG.yaml"

echo """
version: '2'

# This file has been auto-generated

services:
  $CN.$ORG:
    image:        hyperledger/fabric-peer
    container_name: $CN.$ORG
    working_dir:  /opt/gopath/src/github.com/hyperledger/fabric/peer
    command:      peer node start
    logging:
        driver: \"json-file\"
        options:
            max-size: \"200k\"
            max-file: \"10\"
    environment:
      - CORE_VM_ENDPOINT=unix:///host/var/run/docker.sock
      # the following setting starts chaincode containers on the same
      # bridge network as the peers
      # https://docs.docker.com/compose/networking/
      - CORE_VM_DOCKER_HOSTCONFIG_NETWORKMODE=hyperledgerNet
      - CORE_LOGGING_LEVEL=DEBUG
      - CORE_LEDGER_STATE_STATEDATABASE=CouchDB
      - CORE_LEDGER_STATE_COUCHDBCONFIG_USERNAME=admin
      - CORE_LEDGER_STATE_COUCHDBCONFIG_PASSWORD=password
      - CORE_LEDGER_STATE_COUCHDBCONFIG_COUCHDBADDRESS=172.17.0.1:$COUCHDBPORT
      # The following setting skips the gossip handshake since we are
      # are not doing mutual TLS
      - CORE_PEER_ENDORSER_ENABLED=true
      - CORE_PEER_GOSSIP_SKIPHANDSHAKE=true
      - CORE_PEER_GOSSIP_USELEADERELECTION=true
      - CORE_PEER_GOSSIP_ORGLEADER=false
      - CORE_PEER_MSPCONFIGPATH=/etc/hyperledger/crypto-config/peer/msp
      - CORE_PEER_TLS_ENABLED=true
      - CORE_PEER_ID=$CN.$ORG
      - CORE_PEER_LOCALMSPID=${ORG//./-}-MSP
      - CORE_PEER_ADDRESS=$CN.$ORG:7051
      - CORE_PEER_TLS_KEY_FILE=/etc/hyperledger/crypto-config/peer/tlsca/tlsca.$CN.$ORG-key.pem
      - CORE_PEER_TLS_CERT_FILE=/etc/hyperledger/crypto-config/peer/tlsca/tlsca.$CN.$ORG-cert.pem
      - CORE_PEER_TLS_ROOTCERT_FILE=/etc/hyperledger/crypto-config/peer/tlsca.combined.$CN.$ORG-cert.pem
    ports:""" > $FILE


for ((i=0;i<${#PORTS[@]};i+=1))
do
  echo "      - ${PORTS[$i]}" >> $FILE
done

echo """    volumes:
        - /var/run/:/host/var/run/
        - /vagrant/crypto-config/$ORG/peers/$CN.$ORG/:/etc/hyperledger/crypto-config/peer

networks:
  default:
    external:
      name: hyperledgerNet
""" >> $FILE
