#!/usr/bin/env python2
# Created by Guillaume Leurquin, guillaume.leurquin@accenture.com

"""
    create_remote_scripts.py crypto_config.yaml aws_config.json

    Requires GEN_PATH environment variable to be set,
    which points to the hyperledger fabric certificate
    structure created by cryptogen.py
    Creates scripts to remotely connect to the network,
    create and join all channels, and also update the chaincodes remotely
"""

import os
import sys
import json
import yaml
GEN_PATH = os.environ["GEN_PATH"]
DEBUG = False

def fail(msg):
    """Prints the error message and exits"""
    sys.stderr.write('\033[91m' + msg + '\033[0m\n')
    exit(1)

def call(script, *args):
    """Calls the given script using the args"""

    cmd = script + " " + " ".join(args)
    if DEBUG:
        print cmd
    if os.system(cmd) != 0:
        fail("\nERROR: An error occured while executing " + cmd + ". See above for details.")


if len(sys.argv) != 3:
    fail("Usage: create_remote_scripts crypto_config aws_config ")
YAML_CONFIG = sys.argv[1]
AWS_CONFIG = sys.argv[2]


CREATE_AND_JOIN_CHANNELS_REMOTE_SCRIPT = GEN_PATH + '/scripts/create_and_join_channels_remote.sh'
CHAINCODE_REMOTE_SCRIPT = GEN_PATH + '/scripts/update_remote_chaincodes.sh'


SCRIPT_PREAMBLE = """#!/bin/bash
# This file is auto-generated

set -eu -o pipefail

echo "Modifying /etc/hosts..."
INSTALL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
$INSTALL_DIR/set_hosts_public.sh

"""

def create_remote_channel_script(CONF, AWS, channels_remote_script):
    channels_remote_script.write(SCRIPT_PREAMBLE)
    for org in CONF['Orgs']:
        if 'peers' in org and org['peers'] is not None:
            for peer in org['peers']:
                if 'Tools' in peer:
                    channels_remote_script.write("cmd=\"docker exec -it tools.{0} bash -c\"\n".format(org['Domain']))
                    template = "ssh -oStrictHostKeyChecking=no -i {0} -t {1}@tools.{2} $cmd '\"/etc/hyperledger/configtx/create_and_join_channel.sh {3}\"'\n"
                    channels_remote_script.write(template.format(
                        AWS['private_key_path'],
                        AWS['ssh_username'],
                        org['Domain'],
                        peer['Tools']
                    ))

REMOTE_CHAINCODE_SCRIPT_PREAMBLE = """#!/bin/bash
# This file is auto-generated

set -eu -o pipefail
echo "Make sure the channels have been created before running this script"
echo "Make sure that set_public_hosts.sh has been run before running this script"


"""

def create_remote_chaincode_script(CONF, AWS, chaincode_remote_script):
    chaincode_remote_script.write(SCRIPT_PREAMBLE)
    for org in CONF['Orgs']:
        if 'peers' in org and org['peers'] is not None:
            for peer in org['peers']:
                if 'Tools' in peer:
                    chaincode_remote_script.write("cmd=\"docker exec -it tools.{0} bash -c\"\n".format(org['Domain']))
                    template = "ssh -oStrictHostKeyChecking=no -i {0} -t {1}@tools.{2} $cmd '\"/etc/hyperledger/chaincode_tools/update_chaincodes.py --repository {3}\"'\n"
                    chaincode_remote_script.write(template.format(
                        AWS['private_key_path'],
                        AWS['ssh_username'],
                        org['Domain'],
                        AWS['chaincode_github']
                    ))
                    return
    raise Exception('No tools found in the configuration file')

call('mkdir -p', GEN_PATH + "/scripts")

with open(YAML_CONFIG, 'r') as stream:
    with open(AWS_CONFIG, 'r') as aws_stream:
        with open(CREATE_AND_JOIN_CHANNELS_REMOTE_SCRIPT, 'w') as remote_channels_script:
            with open(CHAINCODE_REMOTE_SCRIPT, 'w') as remote_chaincode_script:
                try:
                    CONF = yaml.load(stream)
                    AWS = json.load(aws_stream)

                    create_remote_channel_script(CONF, AWS, remote_channels_script)
                    create_remote_chaincode_script(CONF, AWS, remote_chaincode_script)
                except yaml.YAMLError as exc:
                    print exc

call("chmod +x", CREATE_AND_JOIN_CHANNELS_REMOTE_SCRIPT)
call("chmod +x", CHAINCODE_REMOTE_SCRIPT)
