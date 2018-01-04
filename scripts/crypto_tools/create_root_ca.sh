#!/bin/bash
# Created by Guillaume Leurquin, guillaume.leurquin@accenture.com

set -eu -o pipefail


if [ $# -ne 3 ];
then
	echo ""
	echo "Usage: "
	echo "	createRootCa COMMON_NAME FOLDER_OUT TLS"
	echo "	Creates a self-signed certificate"
	echo "	The certificate will be saved under FOLDER_OUT/COMMON_NAME-cert.pem"
	echo "	The key will be saved under FOLDER_OUT/COMMON_NAME-key.pem"
	echo "	The certificate will contain fields parsed from the COMMON_NAME:"
	echo "		<Whatever>.OU.O.C"
	echo "		Where OU=organisation unit, O=organisation, C=2 letter country code"
	exit 1
fi

INSTALL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PKI="$INSTALL_DIR"/pki
export PKI

rm -d -f -r $PKI
mkdir -p $PKI
touch $PKI/index.txt

CN=$1
FOLDER_OUT=$2
TLS=$3

CA_KEY="$FOLDER_OUT/$CN-key.pem"
CA_CERT="$FOLDER_OUT/$CN-cert.pem"

if [ $TLS = "tlsca" ];
then
	EXTENSIONS=v3_root_ca_or_tls
elif [ $TLS = "ca" ]; then
	EXTENSIONS=v3_root_ca_or_tls
else
	echo "ERROR: Unknown TLS option $TLS. Can only be 'tlsca' or 'ca'." >&2
	exit 1
fi

# split CN in two, first part is the name,
# second the organisational unit, and last the organisation
SUBJECTS=$($INSTALL_DIR/parse_domain_to_subjects.py $CN)

$INSTALL_DIR/create_key.sh $CA_KEY

echo "Creating root certificate..."
openssl req -config $INSTALL_DIR/openssl.cnf \
      -key $CA_KEY \
      -new -x509 -days 7300 -sha256 -extensions $EXTENSIONS \
      -out $CA_CERT \
			-nodes \
			-batch \
			-subj $SUBJECTS \
			-text
echo "Done. Root certificate saved in $CA_CERT"


rm -d -f -r $PKI
