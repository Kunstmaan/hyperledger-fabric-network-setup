#!/bin/bash
# Created by Guillaume Leurquin, guillaume.leurquin@accenture.com

set -eu -o pipefail

if [ $# -ne 2 ];
then
  echo ""
  echo "Usage: "
  echo "  docker_ca COMMON_NAME PORT"
    echo "  COMMON_NAME includes organisation domain"
  echo "  This script creates a docker file to be able to run a hyperledger"
  echo "  fabric CA"
  echo ""
  exit 1
fi

CN=$1
FOLDER=$GEN_PATH/docker
mkdir -p "$FOLDER"
FILE="$FOLDER/$CN.yaml"
PORT=$2
echo """
version: '2'

# This file has been auto-generated

services:
  $CN:
    image:        hyperledger/fabric-ca
    container_name: $CN
    ports:
      - $PORT:7054
    command:      sh -c 'fabric-ca-server start -b admin:adminpw -d'
    logging:
      driver: \"json-file\"
      options:
        max-size: \"200k\"
        max-file: \"10\"
    environment:
      - FABRIC_CA_HOME=/etc/hyperledger/fabric-ca-server
      - FABRIC_CA_SERVER_TLS_ENABLED=true
      - FABRIC_CA_SERVER_CA_CERTFILE=/etc/hyperledger/fabric-ca-server-config/ca/ca.$CN-cert.pem
      - FABRIC_CA_SERVER_CA_KEYFILE=/etc/hyperledger/fabric-ca-server-config/ca/ca.$CN-key.pem
      - FABRIC_CA_SERVER_TLS_CERTFILE=/etc/hyperledger/fabric-ca-server-config/tlsca/tlsca.$CN-cert.pem
      - FABRIC_CA_SERVER_TLS_KEYFILE=/etc/hyperledger/fabric-ca-server-config/tlsca/tlsca.$CN-key.pem
    volumes:
      - /vagrant/crypto-config/$CN/:/etc/hyperledger/fabric-ca-server-config


networks:
  default:
    external:
      name: hyperledgerNet
""" > $FILE
