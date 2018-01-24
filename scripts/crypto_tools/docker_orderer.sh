#!/bin/bash
# Created by Guillaume Leurquin, guillaume.leurquin@accenture.com

set -eu -o pipefail

if [ $# -ne 5 ];
then
	echo ""
	echo "Usage: "
	echo "	docker_orderer COMMON_NAME ORGANISATION PEERS ORGS PORT"
  	echo "  PEERS and ORGS are comma separated"
	echo "  This script creates a docker file to be able to run a hyperledger"
	echo "  fabric orderer"
	echo ""
	exit 1
fi

CN=$1
ORG=$2
Peers=$(echo $3 | tr "," " ") # comma separated peers
declare -a Peers="( $Peers )"
Orgs=$(echo $4 | tr "," " ") # comma separated orgs
Port=$5
declare -a Orgs="( $Orgs )"
FOLDER=$GEN_PATH/docker
mkdir -p "$FOLDER"
FILE="$FOLDER/$CN.$ORG.yaml"

# echo "Peers=${Peers[@]}"
# echo "Orgs=${Orgs[@]}"

echo -n """
version: '2'

# This file has been auto-generated

services:
  $CN.$ORG:
    image:        hyperledger/fabric-orderer
    container_name: $CN.$ORG
    ports:
      - $Port:7050
    working_dir:  /opt/gopath/src/github.com/hyperledger/fabric/orderers
    command:      orderer
	logging:
		driver: \"json-file\"
		options:
			max-size: \"200k\"
			max-file: \"10\"
    environment:
        - ORDERER_GENERAL_LOGLEVEL=debug
        - ORDERER_GENERAL_LISTENADDRESS=0.0.0.0
        - ORDERER_GENERAL_GENESISMETHOD=file
        - ORDERER_GENERAL_GENESISFILE=/etc/hyperledger/configtx/$CN.$ORG.genesis.block
        - ORDERER_GENERAL_LOCALMSPID=${ORG//./-}-MSP
        - ORDERER_GENERAL_LOCALMSPDIR=/etc/hyperledger/crypto-config/orderer/msp
        - ORDERER_GENERAL_TLS_ENABLED=true
        - ORDERER_GENERAL_TLS_ROOTCAS=[/etc/hyperledger/crypto-config/orderer/tlsca/tlsca.$CN.$ORG-cert.pem""" > $FILE

for ((i=0;i<${#Peers[@]};i+=1))
do
  echo -n ",/etc/hyperledger/crypto-config/${Peers[$i]}.${Orgs[$i]}/tlsca/tlsca.${Peers[$i]}.${Orgs[$i]}-cert.pem" >> $FILE
done

echo """]
        - ORDERER_GENERAL_TLS_PRIVATEKEY=/etc/hyperledger/crypto-config/orderer/tlsca/tlsca.$CN.$ORG-key.pem
        - ORDERER_GENERAL_TLS_CERTIFICATE=/etc/hyperledger/crypto-config/orderer/tlsca/tlsca.$CN.$ORG-cert.pem
    volumes:
        - /vagrant/channel/:/etc/hyperledger/configtx
        - /vagrant/crypto-config/$ORG/orderers/$CN.$ORG/:/etc/hyperledger/crypto-config/orderer""" >> $FILE

for ((i=0;i<${#Peers[@]};i+=1))
do
  echo """        - /vagrant/crypto-config/${Orgs[$i]}/peers/${Peers[$i]}.${Orgs[$i]}/:/etc/hyperledger/crypto-config/${Peers[$i]}.${Orgs[$i]}""" >> $FILE
done


echo """
networks:
  default:
    external:
      name: hyperledgerNet
""" >> $FILE
