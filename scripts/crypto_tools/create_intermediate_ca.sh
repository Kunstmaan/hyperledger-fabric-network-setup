#!/bin/bash
# Created by Guillaume Leurquin, guillaume.leurquin@accenture.com

set -eu -o pipefail


if [ $# -ne 6 ];
then
	echo ""
	echo "Usage: "
	echo "	createIntermediateCA COMMON_NAME FOLDER_OUT PARENT_CA TLSCA_OR_CA CAN_SIGN ATTR"
	echo "	Creates an intermediate certificate signed by the PARENT_CA"
	echo "  If TLS_OR_CA is equal to tlsca, will create a server certificate"
	echo "	If TLS_OR_CA is equal to ca, will create a client certificate"
	echo "	CAN_SIGN can be 'True' or 'False'"
	echo " 		Should the certificate be able create intermediate certificates ?"
	echo "	The certificate will be saved under FOLDER_OUT/COMMON_NAME-cert.pem"
	echo "	The key will be saved under FOLDER_OUT/COMMON_NAME-key.pem"
	echo "	The certificate will contain fields parsed from the COMMON_NAME:"
	echo "		<Whatever>.OU.O.C"
	echo "		Where OU=organisation unit, O=organisation, C=2 letter country code"
	exit 1
fi

INSTALL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TLS=$4
CAN_SIGN=$5
ATTR=$6
PKI="$INSTALL_DIR"/pki
export PKI

rm -d -f -r $PKI
mkdir -p $PKI
touch $PKI/index.txt

CN=$1
FOLDER_OUT=$2

CA_PARENT_KEY="$3-key.pem"
CA_PARENT_CERT="$3-cert.pem"
CA_KEY="$FOLDER_OUT/$CN-key.pem"
echo "CA_KEY=$CA_KEY"
CA_CERT="$FOLDER_OUT/$CN-cert.pem"
CA_REQ="$FOLDER_OUT/$CN-req.pem"

SUBJECTS=$($INSTALL_DIR/parse_domain_to_subjects.py $CN)

$INSTALL_DIR/create_key.sh $CA_KEY

mkdir -p $PKI
touch $PKI/index.txt

echo "Creating certificate signing request"
openssl req -config $INSTALL_DIR/openssl.cnf \
      -key $CA_KEY \
      -new -sha256 \
      -out $CA_REQ \
      -nodes \
      -subj $SUBJECTS \
      -text
echo "Done. Request saved in $CA_REQ"

if [ $TLS = "tlsca" ] && [ $CAN_SIGN = "True" ];
then
		EXTENSIONS=v3_intermediate_tls
elif [ $TLS = "tlsca" ] && [ $CAN_SIGN = "False" ]; then
		EXTENSIONS=v3_leaf_tls
elif [ $TLS = "ca" ] && [ $CAN_SIGN = "True" ]; then
		EXTENSIONS=v3_intermediate_ca
elif [ $TLS = "ca" ] && [ $CAN_SIGN = "False" ]; then
		EXTENSIONS=v3_leaf_ca
else
		echo "ERROR: Unknown CAN_SIGN option $CAN_SIGN. Can only be 'True' or 'False'" >&2
		echo "OR Unknown TLS option $TLS. Can only be 'tlsca' or 'ca'." >&2
		exit 1
fi

if [ "$(uname -s)" == "Darwin" ]; then
	SED=gsed
	if ! command -v gsed > /dev/null 2>&1; then {
	  echo "Installing Gsed..."
	  brew install gnu-sed
	  echo "Done."
	}; fi
elif [ "$(uname -s)" == "Linux" ]; then
	SED=sed
fi

# gsed """/\[ v3_leaf_ca \]/aAttributes = test""" openssl.cnf

ATTR="'$ATTR'"
printf "ATTR = $ATTR\n"
# The policy set here (refer to openssl.cnf) defines which fields
# of this intermediate certificate
# must match with a potential certificate that is signed by
# this intermediate certificate
echo "Creating intermediate $TLS certificate..."
# openssl ca -config $INSTALL_DIR/openssl.cnf \
openssl ca -config <($SED "/\[ $EXTENSIONS \]/a1.2.3.4.5.6.7.8.1=ASN1:UTF8String:$ATTR" $INSTALL_DIR/openssl.cnf) \
			-create_serial \
      -days 3650 -md sha256 -extensions $EXTENSIONS -policy policy_loose \
      -in $CA_REQ\
      -out $CA_CERT \
      -outdir $FOLDER_OUT \
      -keyfile $CA_PARENT_KEY \
      -cert $CA_PARENT_CERT \
      -subj $SUBJECTS \
      -batch
	echo "Done. Intermediate certificate saved in $CA_CERT"

pushd $FOLDER_OUT > /dev/null
rm $(find . -type f -not -name "$CN*")
popd > /dev/null

echo "Deleting certificate request"
rm $CA_REQ

rm -d -f -r $PKI
