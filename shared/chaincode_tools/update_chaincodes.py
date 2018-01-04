#!/usr/bin/env python2
# Created by Guillaume Leurquin, guillaume.leurquin@accenture.com
"""
This script pulls the latest version of the chaincode, reads $GOPATH/src/config.json,
and installs/update all the chaincodes according to the config file
"""

import os
import sys
import json
import subprocess
import re

DEBUG = False
GOPATH = os.environ['GOPATH']
CONF_FILE = GOPATH + '/src/chaincodes.json'

def fail(msg):
    """Prints the error message and exits"""
    sys.stderr.write(msg)
    exit(1)

# Parse args
if len(sys.argv) != 2:
    fail("Usage: update_chaincodes repository")
REPOSITORY = sys.argv[1]

def call(script, *args):
    """Calls the given script using the args"""

    cmd = script + " " + " ".join(args)
    if DEBUG:
        print cmd
    proc = subprocess.Popen("bash -c '" + cmd + "'", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, error = proc.communicate()
    if proc.returncode != None and proc.returncode != 0:
        print "Error code:" + str(proc.returncode)
        fail("An error occured while executing " + cmd + ". See above for details. Error:\n" + error)
    return out

def is_installed_or_instantiated(peer, installed, ignore_version=False):
    """Checks if the chaincode is installed or instantiated on the channel"""
    chain_info = call(source_peer(peer), "&&", "peer chaincode",
                      "--cafile", orderer_ca,
                      "--orderer", orderer_host_port,
                      "list",
                      ("--installed" if installed else "--instantiated"),
                      "--channelID", channel_id,
                      "--tls true"
                     )

    pattern = "name:\"" + chaincode_name + "\" version:\"" + (".*" if ignore_version else chaincode_version) + "\" path:\"" + chaincode_path + "\""
    match_obj = re.search(pattern, chain_info)
    if match_obj:
        return True
    return False

def compile_chaincode(cc_language):
    """Compiles the chaincode"""
    if cc_language == "golang":
        print "==> Compiling "+info + "..."
        call("/etc/hyperledger/chaincode_tools/compile_chaincode.sh", chaincode_path)
        print "Done. Compiled "+info + "!"
    elif cc_language == "node":
        print "==> Installing NPM for "+info + "..."
        call("npm", "install", "--prefix", chaincode_path)
        print "Done. Installed NPM for "+info + "!"

def install_chaincode(peer, must_compile_cc, cc_language):
    """Installs chaincode on all the peers"""
    if not is_installed_or_instantiated(peer, installed=True):
        if must_compile_cc:
            compile_chaincode(cc_language)
            must_compile_cc = False
        print "==> Installing " + info + " on " + peer + "..."
        call(source_peer(peer), "&&", "peer chaincode",
             "--cafile", orderer_ca,
             "--orderer", orderer_host_port,
             "install",
             "--name", chaincode_name,
             "--version", chaincode_version,
             "--path", chaincode_path,
             "--lang", chaincode_language
            )
        print "Done. Installed " + info + " on " + peer + "!"
    else:
        print "==> " + info + " is already installed on " + peer + "!"
    return must_compile_cc

def source_peer(peer):
    """Sets environment variables for that peer"""
    return "source /etc/hyperledger/crypto-config/tools/set_env." + peer+".sh"

def instantiate_chaincode(peer):
    """Instantiates chaincode on one of the peers"""
    if not is_installed_or_instantiated(peer, installed=False):
        upgrade = is_installed_or_instantiated(peer, installed=False, ignore_version=True)
        if upgrade:
            print "==> Upgrading " + info + " on " + peer + "..."
        else:
            print "==> Instantiating " + info + " on " + peer + "..."

        call(source_peer(peer), "&&", "peer chaincode",
             "--cafile", orderer_ca,
             "--orderer", orderer_host_port,
             "--logging-level", "debug",
             ("upgrade" if upgrade else "instantiate"),
             "--name", chaincode_name,
             "--version", chaincode_version,
             "--ctor", """\"{\\\"Args\\\":[\\\"Init\\\""""+instantiate_args+"""]}\"""",
             "--channelID", channel_id,
             # "--policy", '\"' + chaincode_policy + '\"', TODO
             "--tls true",
             "--lang", chaincode_language
            )

        if upgrade:
            print "Done. Upgraded " + info + " on " + peer + "!"
        else:
            print "Done. Instantiated " + info + " on " + peer + "!"
    else:
        print "==> " + info + " is already instantiated on " + peer + "!"

def format_args(args):
    """Formats the args with escaped " """
    comma = "," if args else ""
    return comma + ",".join(['\\\"' + a + '\\\"' for a in args])

# First pull latest version of chaincode:
subprocess.call("/etc/hyperledger/chaincode_tools/pull_chaincode.sh {0}".format(REPOSITORY), shell=True)

subprocess.call("npm install --production --prefix " + GOPATH + "/src", shell=True)
subprocess.call("npm run build --prefix " + GOPATH + "/src", shell=True)

with open(CONF_FILE) as chaincodes_stream:
    try:
        for chaincode_path in json.load(chaincodes_stream):
            absolute_chaincode_path = GOPATH + "/src/build/" + chaincode_path
            with open(absolute_chaincode_path + "/package.json") as stream:
                try:
                    chaincode = json.load(stream)
                    chaincode_name = chaincode["name"]
                    chaincode_language = chaincode["hf-language"]
                    chaincode_version = chaincode["version"]

                    must_compile = True
                    if chaincode_language == "node":
                        # Path for node must be absolute
                        print "Using node"
                        chaincode_path = absolute_chaincode_path
                    elif chaincode_language == "golang":
                        # Path for golang must be relative to $GOPATH/src
                        print "Using go"
                    else:
                        fail("Unknown chaincode language " + chaincode_language + " ! Aborting.")

                    info = "chaincode " + chaincode_name + " version " + chaincode_version + " at " + chaincode_path
                    for net_config in chaincode["hf-network"]:
                        channel_id = net_config["channelId"]
                        instantiate_args = format_args(net_config["instantiateArgs"])
                        chaincode_policy = net_config["endorsementPolicy"]
                        orderer_host = net_config["orderer"]["host"]
                        orderer_port = str(net_config["orderer"]["port"])
                        orderer_host_port = orderer_host + ":" + orderer_port
                        orderer_org = ".".join(orderer_host.split(".")[-2:])
                        orderer_ca = "/etc/hyperledger/crypto-config/" + orderer_org + "/orderers/" + orderer_host + "/tlsca.combined." + orderer_host + "-cert.pem"

                        for the_peer in net_config["peers"]:
                            # Install chaincode on all peers
                            must_compile = install_chaincode(the_peer, must_compile, chaincode_language)

                        # Instantiate chaincode on one (the last) of the peers
                        instantiate_chaincode(net_config["peers"][0])
                    print ""

                except ValueError as exc:
                    print exc

    except ValueError as exc:
        print exc
