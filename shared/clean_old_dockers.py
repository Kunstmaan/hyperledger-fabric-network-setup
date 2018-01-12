#!/usr/bin/env python2
# Created by Guillaume Leurquin, guillaume.leurquin@accenture.com


import sys
import subprocess
import argparse

parser = argparse.ArgumentParser(description='Cleans any container with an old version whose name starts with dev- . ATTENTION: Does not work if the peer, chaincode or version contain the minus - character.')
parser.add_argument('--dryrun', action='store_true',
                    help='Shows the commands the script would run, without running them')


args = parser.parse_args()
DRY_RUN = args.dryrun

def fail(msg):
    """Prints the error message and exits"""
    sys.stderr.write('\033[91m' + msg + '\033[0m\n')
    exit(1)

def call(script, *args):
    """Calls the given script using the args"""

    cmd = script + " " + " ".join(args)
    print cmd
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, error = proc.communicate()
    if error != "":
        fail("An error occured while executing " + cmd + ". See above for details. Error=" + error)
    return out


# The output of docker ps sorts the names with the most recent container first
# This is important for the rest of the script, because we want to keep the most
# recent version of each chaincode
output = call("docker ps --format '{{.Names}}' | grep dev-").split('\n')

# Test data, debugging only
# output = ['dev-epeer1.vlaanderen.be-ground_contours-1.0.17', 'dev-epeer1.vlaanderen.be-ground_contours-1.0.16', 'dev-epeer1.vlaanderen.be-ground_contours-1.0.15', 'dev-epeer1.vlaanderen.be-subsidies-1.0.3', 'dev-epeer1.vlaanderen.be-nature_coins-1.0.3', 'dev-epeer1.vlaanderen.be-identity_management-1.0.3', 'dev-epeer1.vlaanderen.be-ground_contours-1.0.14', 'dev-epeer1.vlaanderen.be-access_management-1.0.3', 'dev-epeer1.vlaanderen.be-work_contracts-1.0.3', 'dev-epeer1.vlaanderen.be-nature_management_plan_contours-1.0.3', 'dev-epeer1.vlaanderen.be-certificates-1.0.3', 'dev-epeer1.vlaanderen.be-contours-1.0.3', 'dev-epeer1.vlaanderen.be-nature_coins-1.0.2', 'dev-epeer1.vlaanderen.be-subsidies-1.0.2', 'dev-epeer1.vlaanderen.be-certificates-1.0.2', 'dev-epeer1.vlaanderen.be-contours-1.0.2', 'dev-epeer1.vlaanderen.be-nature_management_plan_contours-1.0.2', 'dev-epeer1.vlaanderen.be-identity_management-1.0.2', 'dev-epeer1.grb.vlaanderen.be-identity_management-1.0.2', 'dev-epeer1.grb.vlaanderen.be-identity_management-1.0.1', '', 'test-test1-cc1-1.0.1', 'test-test1-cc1-1.0.0']

output = filter(None, output) # Remove empty strings

splitted = [s.split('-') for s in output if s.startswith('dev-')]

chaincodes = [ s[-2] for s in splitted]
chaincodes = set(chaincodes)

cache = {}
to_remove = []

for idx, splitted_name in enumerate(splitted):
    peer = splitted_name[1]
    for chaincode in chaincodes:
        if chaincode == splitted_name[-2]:
            if peer in cache and chaincode in cache[peer]:
                to_remove.append(output[idx])
            else:
                if peer in cache:
                    cache[peer].append(chaincode)
                else:
                    cache[peer] = [chaincode]


cmds = ["docker rm -f {0}".format(name) for name in to_remove]
if DRY_RUN:
    for cmd in cmds:
        print cmd
else:
    for cmd in cmds:
        call(cmd)
