#!/bin/bash
# Created by Guillaume Leurquin, guillaume.leurquin@accenture.com

set -eu -o pipefail

if [ $# -ne 2 ];
then
  echo ""
  echo "Usage: "
  echo "  docker_tools ORG CHANNEL"
  echo "  This script creates a docker file to be able to run a hyperledger"
  echo "  fabric tools CLI"
  echo ""
  exit 1
fi

ORG=$1
CHANNEL=$2
FOLDER=$GEN_PATH/docker
mkdir -p "$FOLDER"
FILE="$FOLDER/tools.$ORG.yaml"

echo """
version: '2'

# This file has been auto-generated

services:
  tools.$ORG:
    image:        hyperledger/fabric-tools
    tty:          true
    working_dir:  /etc/hyperledger
    container_name: tools.$ORG
    # command: /etc/hyperledger/create_and_join_public_channel.sh $CHANNEL
    environment:
      - CORE_VM_DOCKER_HOSTCONFIG_NETWORKMODE=hyperledgerNet
      - GOPATH=/opt/gopath
      - CORE_VM_ENDPOINT=unix:///host/var/run/docker.sock
      - CORE_LOGGING_LEVEL=DEBUG
      - CORE_PEER_GOSSIP_SKIPHANDSHAKE=true
      - CORE_PEER_GOSSIP_USELEADERELECTION=true
      - CORE_PEER_GOSSIP_ORGLEADER=false
      - CORE_PEER_TLS_ENABLED=true
    volumes:
      - /vagrant/channel/:/etc/hyperledger/configtx
      - /vagrant/crypto-config/:/etc/hyperledger/crypto-config/
      - /vagrant/shared/:/etc/hyperledger/
      - /vagrant/ssh/:/root/.ssh/

networks:
  default:
    external:
      name: hyperledgerNet

""" > $FILE
