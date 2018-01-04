#!/usr/bin/env python2
# Created by Guillaume Leurquin, guillaume.leurquin@accenture.com


import os
import sys
import yaml

# Note: configtxgen requires certificates to have the subjectKeyIdentifier extension

DEBUG = False
# Path to where crypto-config and docker folders will be generated
GEN_PATH = os.environ["GEN_PATH"]

PWD = os.path.dirname(__file__)
CONFIGTX_FILENAME = GEN_PATH + "/channel/configtx.yaml"
ARTIFACT_SCRIPT_NAME = "create_channel_artifacts.sh"
ARTIFACT_SCRIPT = GEN_PATH + '/channel/' + ARTIFACT_SCRIPT_NAME
CREATE_AND_JOIN_CHANNEL_SCRIPT = GEN_PATH + '/channel/create_and_join_channel.sh'


DEVMODE_ARTIFACT_SCRIPT_NAME = 'create_devmode_channel_artifacts.sh'

DEVMODE_ARTIFACT_SCRIPT = GEN_PATH + "/channel/" + DEVMODE_ARTIFACT_SCRIPT_NAME
DEVMODE_CHANNEL_SCRIPT = GEN_PATH + "/devmode/script.sh"

def fail(msg):
    """Prints the error message and exits"""
    sys.stderr.write(msg)
    exit(1)

# Parse args
if len(sys.argv) != 2:
    fail("Usage: gen_configtx config.yaml")
YAML_CONFIG = sys.argv[1]

def call(script, *args):
    """Calls the given script using the args"""

    cmd = script + " " + " ".join(args)
    if DEBUG:
        print cmd
    if os.system(cmd) != 0:
        fail("\nAn error occured while executing " + cmd + ". See above for details.")

def to_pwd(script):
    """Converts the script path to the correct path"""
    return PWD + "/" + script

def add_org(org_conf):
    """Returns the org config for configtx"""
    msp_name = org_conf['Domain'].replace('.', '-') + '-MSP'

    yaml_org = """
    - &{0}
      Name: {0}
      # ID to load the MSP definition as
      # ID must match ID given in docker file
      ID: {1}
      MSPDir: ../crypto-config/{2}/msp""".format(org_conf['Name'], msp_name, org_conf['Domain'])

    if 'peers' in org_conf and org_conf['peers']:
        peer = org_conf['peers'][0]
        yaml_org = yaml_org + """
      AnchorPeers:
        # AnchorPeers defines the location of peers which can be used
        # for cross org gossip communication.  Note, this value is only
        # encoded in the genesis block in the Application section context
        - Host: {0}
          Port: {1}""".format(peer['Hostname'] + '.' + org_conf['Domain'], peer['Ports'][0].split(':')[0])
    return yaml_org + '\n'


PROFILE_SECTION = """
################################################################################
#
#   Profile
#
#   - Different configuration profiles may be encoded here to be specified
#   as parameters to the configtxgen tool
#
################################################################################


# Organizations inside a consortium are the owners of the orderer. They can do administration tasks.

Profiles:
"""


all_consortiums = []

def add_orderer(orderer_conf, org_conf):

    consortiums = []
    for cons in orderer_conf['Consortiums']:
        consortium_name = "        " + cons["Name"] + ':\n'
        orgs = "          Organizations:\n"
        consortium_members = '\n'.join(["            - *" + orgName for orgName in cons['Organizations']])
        consortiums.append(consortium_name+orgs+consortium_members)
    consortiums = '\n'.join(consortiums)
    all_consortiums.append(consortiums)
    admin_orgs = '\n'.join(["          - *" + org for org in orderer_conf['AdminOrgs']])
    ord_addresses = '\n'.join(["          - "+orderer_conf['Hostname'] + '.' + org_conf['Domain'] + ':' + str(orderer_conf['Port'])])
    return """
    {0}genesis:
      Orderer:
        <<: *Orderer
        Addresses:
{1}
        Organizations:
{2}
      Consortiums:
{3}
""".format(
    (orderer_conf['Hostname'] + org_conf['Domain']).replace('.', ''),
    ord_addresses,
    admin_orgs,
    consortiums
)

def add_channel(channel_conf):
    channel_orgs = '\n'.join(["          - *" + org for org in channel_conf['Organizations']])
    return """
    {0}:
      Consortium: {1}
      Application:
        <<: *ApplicationDefaults
        Organizations:
{2}
""".format(channel_conf['Name'], channel_conf['Consortium']['Name'], channel_orgs)

def add_channel_script(channel_name):
    return """
echo "Generating {0} configuration transaction '{0}.tx'"
configtxgen -profile {0} -channelID {0} -outputCreateChannelTx $PREFIX/{0}.tx
if [ "$?" -ne 0 ]; then
  echo "Failed to generate {0} configuration transaction..." >&2
  exit 1
fi
echo "Done"
echo "-----"
""".format(channel_name)

def add_orderer_script(orderer_conf, org_conf):

    orderer_cn = orderer_conf["Hostname"] + '.' + org_conf["Domain"]
    return """
echo "Generating {0} Genesis Block..."
configtxgen -profile {1}genesis -channelID {1}genesis -outputBlock $PREFIX/{0}.genesis.block
if [ "$?" -ne 0 ]; then
  echo "Failed to generate {0} channel configuration transaction..." >&2
  exit 1
fi
echo "Done"
echo "-----"
""".format(
    orderer_cn,
    orderer_cn.replace('.', '')
)

ORDERER_DEVMODE_SCRIPT = """
echo "Generating devmode Genesis Block..."
configtxgen -profile devmodeorderergenesis -channelID devmodeorderergenesis -outputBlock $PREFIX/orderer.genesis.block
if [ "$?" -ne 0 ]; then
  echo "Failed to generate devmode channel configuration transaction..." >&2
  exit 1
fi
echo "Done"
echo "-----"
"""

def add_devmode(conf):
    return"""
    devmodeorderergenesis:
      Orderer:
        <<: *Orderer
        Addresses:
          - orderer:7050
        Organizations:
          - *{1} # Single organisation
      Consortiums:
        # All consortiums
{0}
""".format('\n'.join(all_consortiums), conf['Devmode']['Name'])

def get_all_hosts_and_orderer_from_channel(CONF, channel_conf):
    orderers_for_channel = []
    peers_for_channel = []

    def get_peers_from_org(org):
        if 'peers' in org and org['peers']:
            return [{'peer_name':peer['Hostname'], 'peer_org':org["Domain"]} for peer in org['peers']]
        return []

    for org in CONF['Orgs']:
        if org['Name'] in channel_conf['Organizations']:
            peers_for_channel.extend(get_peers_from_org(org))

        if 'orderers' in org and org['orderers']:
            for orderer in org['orderers']:
                if channel_conf['Name'] in orderer['Channels']:
                    orderers_for_channel.append({'ord_org': org['Domain'], 'ord_name': orderer['Hostname']})


    if len(orderers_for_channel) == 0:
        fail('No orderer for channel '+channel_conf['Name'])

    if len(peers_for_channel) == 0:
        fail('No peers for channel '+channel_conf['Name'])


    return {
        'channel': channel_conf['Name'],
        'peers': peers_for_channel,
        'orderer': orderers_for_channel[0] # Maybe that all the orderers are needed. Needs testing TODO
    }

CHANNEL_SCRIPT_PREAMBLE = """#!/bin/bash
# This file is auto-generated

# This file allows you to create and join a channel. It requires
# channel_tools.sh to be sourced for all commands to work

set -eu -o pipefail

if [ $# -ne 1 ];
then
	echo ""
	echo "Usage: "
	echo "	create_and_join_channel CHANNEL_ID"
	exit 1
fi

. /etc/hyperledger/configtx/channel_tools.sh

channel_id=$1


"""


def create_channel_script(CONF, channel_script):
    i = 0
    channel_script.write(CHANNEL_SCRIPT_PREAMBLE)
    for channel in CONF['Channels']:
        channel_info = get_all_hosts_and_orderer_from_channel(CONF, channel)
        wait_for_host = '\n'.join(['  wait_for_host ' + peer['peer_name'] + '.' + peer['peer_org'] for peer in channel_info['peers']]) + '\n'

        channel_orderer = "  channel_orderer={0}\n".format(channel_info['orderer']['ord_name'])
        channel_orderer_org = "  channel_orderer_org={0}\n".format(channel_info['orderer']['ord_org'])

        create_channel = '  create_channel {0} {1} $channel_orderer $channel_orderer_org $channel_id\n'.format(
            channel_info['peers'][0]['peer_name'],
            channel_info['peers'][0]['peer_org']
        )

        join_channel = []
        for peer in channel_info['peers']:
            join_channel.append('  join_channel {0} {1} $channel_orderer $channel_orderer_org $channel_id'.format(
                peer['peer_name'],
                peer['peer_org']
            ))
        join_channel = '\n'.join(join_channel) + '\n'
        channel_script_content = channel_orderer + channel_orderer_org + '\n' + wait_for_host + '\n' + create_channel + join_channel

        if i == 0:
            channel_script.write('if [ $channel_id == "{0}" ]; then\n'.format(channel['Name']))
        else:
            channel_script.write('elif [ $channel_id == "{0}" ]; then\n'.format(channel['Name']))

        channel_script.write(channel_script_content)

        if i == len(CONF['Channels']) - 1:
            channel_script.write('else\n  puts "Unknown channel id $channel_id"\nfi')
        i += 1


DEVMODE_ARTIFACT_SCRIPT_PREAMBLE = """#!/bin/bash
# This file is auto-generated
set -eu -o pipefail

PREFIX="../devmode/channel"
rm -rf $PREFIX
mkdir -p $PREFIX

FABRIC_CFG_PATH=$(pwd)
export FABRIC_CFG_PATH
echo FABRIC_CFG_PATH=$FABRIC_CFG_PATH

"""

DEVMODE_CHANNEL_SCRIPT_PREAMBLE = """#!/bin/bash
# Copyright London Stock Exchange Group All Rights Reserved.
#
# SPDX-License-Identifier: Apache-2.0
set -eu -o pipefail

# This script expedites the chaincode development process by automating the
# requisite channel create/join commands

# This file is auto-generated
"""

DEVMODE_CHANNEL_SCRIPT_END = """
# Now the user can proceed to build and start chaincode in one terminal
# And leverage the CLI container to issue install instantiate invoke query commands in another

#we should have bailed if above commands failed.
#we are here, so they worked
sleep 600000
exit 0
"""


call("mkdir -p", GEN_PATH + "/channel")
call("mkdir -p", GEN_PATH + "/devmode")
call("cp", to_pwd("configtxBase.yaml"), CONFIGTX_FILENAME)

ARTIFACT_SCRIPT_PREAMBLE = """#!/bin/bash
# This file is auto-generated

set -eu -o pipefail

FABRIC_CFG_PATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export FABRIC_CFG_PATH
echo FABRIC_CFG_PATH=$FABRIC_CFG_PATH
rm -rf *.tx
rm -rf *.block

PREFIX="."

"""


with open(YAML_CONFIG, 'r') as stream:
    with open(CONFIGTX_FILENAME, 'a') as configtx:
        with open(ARTIFACT_SCRIPT, 'w') as art_script:
            with open(DEVMODE_ARTIFACT_SCRIPT, 'w') as devmode_artifact_script:
                with open(DEVMODE_CHANNEL_SCRIPT, 'w') as devmode_channel_script:
                    with open(CREATE_AND_JOIN_CHANNEL_SCRIPT, 'w') as channel_script:
                        try:
                            CONF = yaml.load(stream)
                            art_script.write(ARTIFACT_SCRIPT_PREAMBLE)
                            devmode_artifact_script.write(DEVMODE_ARTIFACT_SCRIPT_PREAMBLE)
                            devmode_channel_script.write(DEVMODE_CHANNEL_SCRIPT_PREAMBLE)

                            for theOrg in CONF["Orgs"]:
                                configtx.write(add_org(theOrg))

                            configtx.write(PROFILE_SECTION)
                            for theChannel in CONF["Channels"]:
                                configtx.write(add_channel(theChannel))
                                the_channel_script = add_channel_script(theChannel["Name"])
                                devmode_artifact_script.write(the_channel_script)
                                art_script.write(the_channel_script)
                                devmode_channel_script.write("""
peer channel create -c {0} -f channel/{0}.tx -o orderer:7050
peer channel join -b {0}.block\n\n""".format(theChannel['Name']))

                            create_channel_script(CONF, channel_script)
                            devmode_artifact_script.write(ORDERER_DEVMODE_SCRIPT)

                            for theOrg in CONF["Orgs"]:
                                if 'orderers' in theOrg and theOrg['orderers']:
                                    for theOrderer in theOrg['orderers']:
                                        configtx.write(add_orderer(theOrderer, theOrg))
                                        art_script.write(add_orderer_script(theOrderer, theOrg))

                            configtx.write(add_devmode(CONF))
                            devmode_channel_script.write(DEVMODE_CHANNEL_SCRIPT_END)

                            call(to_pwd("create_dev_docker_compose.py"), CONF['Devmode']['Domain'], CONF['Devmode']['peers'][0]['Hostname'], CONF['Devmode']['admins'][0]['Hostname'])
                        except yaml.YAMLError as exc:
                            print exc

call("chmod +x", ARTIFACT_SCRIPT)
call("chmod +x", CREATE_AND_JOIN_CHANNEL_SCRIPT)
call("chmod +x", DEVMODE_CHANNEL_SCRIPT)
call("chmod +x", DEVMODE_ARTIFACT_SCRIPT)
call("cp", to_pwd('channel_tools.sh'), GEN_PATH + '/channel')
call("mkdir -p", GEN_PATH + '/devmode/chaincode')


call('pushd', GEN_PATH + '/channel', '&&', './' + DEVMODE_ARTIFACT_SCRIPT_NAME, '&&', "popd")
call('pushd', GEN_PATH + '/channel', '&&', './' + ARTIFACT_SCRIPT_NAME, '&&', "popd")
