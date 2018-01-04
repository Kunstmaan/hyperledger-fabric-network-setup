#!/bin/bash
# Created by Guillaume Leurquin, guillaume.leurquin@accenture.com

set -eu -o pipefail


if [ $# -ne 1 ];
then
	echo ""
	echo "Usage: "
	echo "	createKey KEY_NAME"
	echo "	Creates an elliptic curve key with name KEY_NAME"
	exit 1
fi

CA_KEY=$1

INSTALL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PKI="$INSTALL_DIR"/pki
export PKI

echo "Creating key..."
openssl ecparam -name prime256v1 -genkey -noout -out $CA_KEY.tmp
echo "Converting key to pkcs8"
openssl pkcs8 -topk8 -inform PEM -outform PEM -nocrypt -in $CA_KEY.tmp -out $CA_KEY
rm $CA_KEY.tmp
echo "Done. Key saved in $CA_KEY"

rm -d -f -r $PKI
