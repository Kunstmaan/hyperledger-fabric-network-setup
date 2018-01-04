#!/usr/bin/env python2
# Created by Guillaume Leurquin, guillaume.leurquin@accenture.com

"""
    get_hosts_scripts.py aws_config

    Requires GEN_PATH environment variable to be set,
    which points to the hyperledger fabric certificate
    structure created by cryptogen.py

    Creates clean_hosts.sh, set_hosts_public.sh, set_hosts_private.sh
    and update_remote_apps.sh

    These scripts allow you to modify /etc/hosts file to resolve
    the names of your network to IP addresses running on Amazon

    Note: set_hosts_public.sh will only be created if you are the one
    who ran vagrant up (and that you have a .vagrant folder)
"""

import os
import sys
import json
import subprocess
import yaml

DEBUG = False

PWD = os.path.dirname(__file__)
VAGRANT_FOLDER = PWD+'/../.vagrant'
GEN_PATH = os.environ["GEN_PATH"]

def fail(msg):
    """Prints the error message and exits"""
    sys.stderr.write('\033[91m' + msg + '\033[0m\n')
    exit(1)

# Parse args
if len(sys.argv) != 3:
    fail("Usage: get_hosts_scripts aws_config do_public")
AWS_CONF = json.load(open(sys.argv[1]))
DO_PUBLIC = sys.argv[2] == 'True'

def call(script, *args):
    """Calls the given script using the args"""

    cmd = script + " " + " ".join(args)
    if DEBUG:
        print cmd
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, error = proc.communicate()
    if error != "":
        fail("An error occured while executing " + cmd + ". See above for details. Error=" + error)
    return out

def get_container_name(yaml_file):
    """Returns the container name of the yaml_file docker compose file"""
    docker_path = GEN_PATH + "/docker/"
    with open(docker_path + yaml_file, 'r') as stream:
        try:
            conf = yaml.load(stream)
            return conf['services'].keys()[0]

        except yaml.YAMLError as exc:
            print exc


def remove_line_matching_from_hosts(dns_name):
    """Removes the first line that contains dns_name from /etc/hosts"""
    return "sudo sed -i.bak '/" + dns_name + "/d' /etc/hosts && sudo rm /etc/hosts.bak\n"


def add_entry_to_hosts(to_add):
    """Returns the command to add something to the hosts file"""
    return "sudo bash -c \"echo " + to_add + " >> /etc/hosts\"\n"

def clean_known_hosts(dns_name):
    """Command to remove the entry in known_hosts"""
    return "sed -i.bak '/"+dns_name.lower()+"/d' ~/.ssh/known_hosts && rm ~/.ssh/known_hosts.bak\n"

PREAMBLE = """#!/bin/bash
# This file has been auto-generated

"""


call("mkdir -p", GEN_PATH + "/scripts")


if DO_PUBLIC:
    SCRIPT_OUT_PUBLIC_FN = GEN_PATH + "/scripts/set_hosts_public.sh"
    SCRIPT_OUT_PUBLIC = open(SCRIPT_OUT_PUBLIC_FN, "w")
    SCRIPT_OUT_PUBLIC.write(PREAMBLE)
    SCRIPT_OUT_PUBLIC.write("# This script automatically adds entries from the /etc/hosts file\n\n")
else:
    print '{0} does not exist. Did you run vagrant up ?\n'.format(VAGRANT_FOLDER)

SCRIPT_OUT_PRIVATE_FN = GEN_PATH + "/scripts/set_hosts_private.sh"
SCRIPT_OUT_PRIVATE = open(SCRIPT_OUT_PRIVATE_FN, "w")
SCRIPT_OUT_PRIVATE.write(PREAMBLE)
SCRIPT_OUT_PRIVATE.write("# This script automatically adds entries from the /etc/hosts file\n\n")

SCRIPT_CLEANER_FN = GEN_PATH + "/scripts/clean_hosts.sh"
SCRIPT_CLEANER = open(SCRIPT_CLEANER_FN, "w")
SCRIPT_CLEANER.write(PREAMBLE)
SCRIPT_CLEANER.write("# This script removes automatically generated entries from the /etc/hosts file\n\n")

SCRIPT_APPS_FN = GEN_PATH + "/scripts/update_remote_apps.sh"
SCRIPT_APPS = open(SCRIPT_APPS_FN, "w")
SCRIPT_APPS.write(PREAMBLE)
SCRIPT_APPS.write("# This script automatically updates the apps on the AWS network,\n")
SCRIPT_APPS.write("# by calling apps/install_app.sh with the app's name as parameted\n")
SCRIPT_APPS.write("# Should be called from local computer (not from within the network)\n\n")
SCRIPT_APPS.write("""set -eu -o pipefail

echo "Modifying /etc/hosts..."
INSTALL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
$INSTALL_DIR/set_hosts_public.sh
echo "If the process hangs here, exit this shell and try again. (reloads /etc/hosts)"

""")



for instance in AWS_CONF["ec2s"]:
    instance_name = "Hyperledger_"+instance
    instance_id = "$(cat {0}/machines/".format(VAGRANT_FOLDER) + instance_name + "/aws/id)"
    if DO_PUBLIC:
        public_ip = call("aws ec2 describe-instances --filter \"Name=instance-id,Values=" + instance_id + "\" --query 'Reservations[0].Instances[0].PublicIpAddress'")
        public_ip = public_ip.rstrip("\n").rstrip('"').lstrip('"')
    private_ip = AWS_CONF["ec2s"][instance]["ip"]
    for docker_container in AWS_CONF["ec2s"][instance]["fabric"]:
        docker_name = get_container_name(docker_container["docker"])
        host_value_private = private_ip + " " + docker_name

        remove_line = remove_line_matching_from_hosts(docker_name)

        if DO_PUBLIC:
            host_value_public = public_ip + " " + docker_name
            SCRIPT_OUT_PUBLIC.write(clean_known_hosts(docker_name))
            SCRIPT_OUT_PUBLIC.write(remove_line)
            SCRIPT_OUT_PUBLIC.write(add_entry_to_hosts(host_value_public))
            SCRIPT_OUT_PUBLIC.write("\n")


        SCRIPT_OUT_PRIVATE.write(clean_known_hosts(docker_name))
        SCRIPT_OUT_PRIVATE.write(remove_line)
        SCRIPT_OUT_PRIVATE.write(add_entry_to_hosts(host_value_private))
        SCRIPT_OUT_PRIVATE.write("\n")

        SCRIPT_CLEANER.write(clean_known_hosts(docker_name))
        SCRIPT_CLEANER.write(remove_line)
        SCRIPT_CLEANER.write("\n")

    for app in AWS_CONF["ec2s"][instance]["apps"]:
        hostname = docker_name = get_container_name(AWS_CONF["ec2s"][instance]["fabric"][0]["docker"])
        user = AWS_CONF["ssh_username"]
        ssh_key = AWS_CONF["private_key_path"]
        SCRIPT_APPS.write("echo \"Updating "+app+" app...\"\n")
        SCRIPT_APPS.write("ssh -i "+ssh_key+" -t "+user+"@"+hostname+" /vagrant/apps/install_app.sh "+app+"\n\n")

if DO_PUBLIC:
    call("chmod +x", SCRIPT_OUT_PUBLIC_FN)
    SCRIPT_OUT_PUBLIC.close()

call("chmod +x", SCRIPT_OUT_PRIVATE_FN)
SCRIPT_OUT_PRIVATE.close()
call("chmod +x", SCRIPT_CLEANER_FN)
SCRIPT_CLEANER.close()
call("chmod +x", SCRIPT_APPS_FN)
SCRIPT_APPS.close()
