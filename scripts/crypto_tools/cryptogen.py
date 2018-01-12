#!/usr/bin/env python2
# Created by Guillaume Leurquin, guillaume.leurquin@accenture.com

"""Cryptogen.py crypto-config.yaml override

This module creates certificate structure for hyperledger fabric, along with
the docker compose files used to boot the network

It takes as first argument a .yaml file containing the structure of the network.
The second argument is a boolean which defines if the files should be overriden or not.
It requires the environment variable GEN_PATH to be set, which is the path
where the generated files will be saved.

It will also generate channel artifacts if the organisation MSP changed
"""


import os
import sys
import json
from argparse import ArgumentParser
import yaml

DEBUG = False
# Takes cryptoconfig.yaml as first argument
# Path in which the scripts are
PWD = os.path.dirname(__file__)
# Path to where crypto-config and docker folders will be generated
GEN_PATH = os.environ["GEN_PATH"]

ORG_MSP_CHANGED = False

def fail(msg):
    """Prints the error message and exits"""
    sys.stderr.write('\033[91m' + msg + '\033[0m\n')
    exit(1)

PARSER = ArgumentParser(description='Creates the channel artifacts and the channel creation/joining scripts')
PARSER.add_argument('crypto_config', type=str, help='cryptographic configuration of the network, as YAML file. See the provided example for details.')
PARSER.add_argument('--configtxBase', help='path to configtx hyperledger fabric config file, without the organisations and profiles (they will be generated). Defaults to a simple orderer configuration.', action='store')
PARSER.add_argument('--noOverride', help='Do not override existing files (default: override files). Useful if you want to add more users. If this is not set, will delete the generated folder and generate everything from scratch', action='store_true')

args = PARSER.parse_args()
YAML_CONFIG = args.crypto_config
OVERRIDE = not args.noOverride
CONFIGTX_BASE = "--configtxBase {0}".format(args.configtxBase) if args.configtxBase else ""

EXPLORER_DATA_PROD = {
    "network-config": {

    },
    "host": "localhost",
    "port": "8080",
    "GOPATH": "../artifacts",
    "keyValueStore": "/tmp/fabric-client-kvs",
    "eventWaitTime": "30000",
    "mysql": {
        "host": "mysql",
        "port": "3306",
        "database": "fabricexplorer",
        "username": "root",
        "passwd": "password"
    }
}

EXPLORER_DATA_DEV = {
    "network-config": {

    },
    "host": "localhost",
    "port": "8080",
    "GOPATH": "../artifacts",
    "keyValueStore": "/tmp/fabric-client-kvs",
    "eventWaitTime": "30000",
    "mysql": {
        "host": "mysql",
        "port": "3306",
        "database": "fabricexplorer",
        "username": "root",
        "passwd": "password"
    }
}

# ORG_MAP = {
#     'currentId': 1
#     'grb.vlaanderen.be': {
#         'id': 1
#         'peers': {
#             'currentId': 1
#             'peer1.vlaanderen.be': {
#                 'id': 1
#             }
#         }
#     }
# }

# used for fabric-explorer
ORG_MAP = {
    'currentId': 0
}

def call(script, *args):
    """Calls the given script using the args"""

    cmd = script + " " + " ".join(args)
    if DEBUG:
        print cmd
    if os.system(cmd) != 0:
        fail("\nERROR: An error occured while executing " + cmd + ". See above for details.")

def to_pwd(script):
    """Converts the script path to the correct path"""
    return PWD + "/" + script

def to_domain(pre, org):
    """Appends pre to org to create a domain name"""
    return pre + "." + org["Domain"]

def create_peer_docker(peer, org):
    """Creates a docker compose file for this peer"""
    # Create peer docker
    call(
        to_pwd("docker_peer.sh"),
        peer["Hostname"],
        org["Domain"],
        ",".join(peer["Ports"]),
        str(peer["CouchdbPort"]),
        )

    if "Tools" in peer:
        call(to_pwd("docker_tools.sh"), org["Domain"], peer["Tools"])

    call(
        to_pwd("create_peer_env.sh"),
        peer["Hostname"],
        peer["Ports"][0].split(":")[0],
        org["Domain"],
        org["admins"][0]["Hostname"],
        CRYPTO_CONFIG_PATH + org["Domain"]
    )

def get_org_nb(org):
    global ORG_MAP
    return 'org'+str(ORG_MAP[org['Domain']]['id'])

def add_admin_to_explorer(org, admin, is_dev = False):
    """Adds an admin to this organisation, for fabric-explorer"""
    if 'peers' in org and org['peers']>0:
        org_nb = get_org_nb(org)
        global EXPLORER_DATA_PROD
        global EXPLORER_DATA_DEV

        explorer = EXPLORER_DATA_DEV if is_dev else EXPLORER_DATA_PROD
        if(is_dev):
            org_nb = 'org1'

        if 'admin' not in explorer['network-config'][org_nb]:
            base = '/crypto-config/{0}/users/{1}.{0}/msp/'.format(org['Domain'], admin['Hostname'])
            explorer['network-config'][org_nb]['admin'] = {
                'key': base+'keystore',
                'cert': base+'signcerts'
            }
            explorer['network-config'][org_nb]['name'] = org['Domain']
            explorer['network-config'][org_nb]['mspid'] = org['Domain'].replace('.', '-') + '-MSP'

def add_peer_to_explorer(org, peer, is_dev = False):
    # Also add this to the explorer data
    if 'peers' in org and org['peers']>0:
        global ORG_MAP
        global EXPLORER_DATA_PROD
        global EXPLORER_DATA_DEV

        explorer = EXPLORER_DATA_DEV if is_dev else EXPLORER_DATA_PROD

        peerData = ORG_MAP[org['Domain']]['peers']
        peerData['currentId'] += 1
        peerDomain = peer['Hostname'] + '.' + org['Domain']
        peerData[peerDomain] = {
            'id': peerData['currentId']
        }
        org_nb = get_org_nb(org)
        peer_nb = 'peer' + str(peerData['currentId'])
        requestsPort = peer['Ports'][0].split(':')[0]
        eventsPort = peer['Ports'][1].split(':')[0]
        cacert = '/crypto-config/{0}/peers/{1}/tlsca.combined.{1}-cert.pem'.format(org['Domain'], peerDomain)
        if is_dev:
            org_nb = 'org1'
            peer_nb = 'peer1'
            peerDomain = 'peer'
            requestsPort = '7051'
            eventsPort = '7051'
        explorer['network-config'][org_nb][peer_nb] = {
            'requests': 'grpc{2}://{0}:{1}'.format(peerDomain, requestsPort, ('' if is_dev else 's')),
            'events': 'grpc{2}://{0}:{1}'.format(peerDomain, eventsPort, ('' if is_dev else 's')),
            'server-hostname': peerDomain,
            'tls_cacerts': cacert
        }

def create_orderer_docker(orderer, org):
    """Creates a docker compose file for this orderer"""
    # Create orderers docker
    peer_cn = []
    peer_orgs = []
    for peer in orderer["Peers"]:
        peer_cn.append(peer["Hostname"])
        peer_orgs.append(peer["Org"])

    call(
        to_pwd("docker_orderer.sh"),
        orderer["Hostname"],
        org["Domain"],
        ",".join(peer_cn),
        ",".join(peer_orgs),
        str(orderer["Port"])
        )

def create_docker(role, component, org):
    """Creates docker files for the given role"""
    if role == "peers":
        create_peer_docker(component, org)
    elif role == "orderers":
        create_orderer_docker(component, org)
    elif role == "ca":
        call(to_pwd("docker_ca.sh"), component['Domain'], str(component['Port']))

def create_msp_struct(msp_folder):
    """Creates the msp directory structure"""
    call("mkdir -p", msp_folder + "/admincerts")
    call("mkdir -p", msp_folder + "/cacerts")
    call("mkdir -p", msp_folder + "/intermediatecerts")
    call("mkdir -p", msp_folder + "/tlscacerts")
    call("mkdir -p", msp_folder + "/tlsintermediatecerts")

def remove_cert(filename):
    """Removes suffix -cert.pem from filename"""
    return filename[:-9] # -cert.pem --> 9 chars

def create_msp(org_domain, ca_paths, is_tls, subfolder, is_admin):
    """Creates and fills the MSP folder with certificates"""
    user_folder = CRYPTO_CONFIG_PATH + org_domain + "/" + subfolder
    msp_folder = user_folder + "/msp"
    create_msp_struct(msp_folder)
    org_admincerts = CRYPTO_CONFIG_PATH + org_domain + "/msp/admincerts/"
    is_not_org = "users" in subfolder or "peers" in subfolder or "orderers" in subfolder

    if "users" in subfolder and not is_tls:
        if is_admin:
            call("cp", ca_paths[-1], msp_folder + "/admincerts")
            call("cp -r", ca_paths[-1], org_admincerts)
        call(PWD + "/signingIdentity/generateSigningIdentity.sh", user_folder)

    if is_not_org and not is_tls:
        call("cp -r", org_admincerts, msp_folder + "/admincerts")

    inter_cas = ca_paths[1::]
    if is_not_org:
        inter_cas = inter_cas[:-1] # Remove last one

    if is_tls:
        call("cp", ca_paths[0], msp_folder + "/tlscacerts")
        for tlsca_path in inter_cas:
            call("cp", tlsca_path, msp_folder + "/tlsintermediatecerts")
    else:
        call("cp", ca_paths[0], msp_folder + "/cacerts")
        for inter_ca_path in inter_cas:
            call("cp", inter_ca_path, msp_folder + "/intermediatecerts")
        if is_not_org:
            call("mkdir -p", msp_folder + "/keystore")
            call("mkdir -p", msp_folder + "/signcerts")
            call("cp", ca_paths[-1], msp_folder + "/signcerts")
            call("cp", remove_cert(ca_paths[-1]) + "-key.pem", msp_folder + "/keystore")

def copy_admincerts_to_admins(org):
    """
        After creating the admins, the organisation's folder contains in admincerts all the
        certificates of the admins. But these admin's folders must also contain all the other
        admins certificates. This copies the org admincerts to the admin's admincerts.
    """
    for admin in org["admins"]:
        domain_path = CRYPTO_CONFIG_PATH + org["Domain"]
        org_admincerts = domain_path + "/msp/admincerts/"
        admin_admincerts = domain_path + "/users/" + admin["Hostname"] + "." + org['Domain'] + "/msp/admincerts"
        call("cp -r", org_admincerts, admin_admincerts)

def create_all_msp(org):
    """Creates all msps for the org"""
    create_ca(org["ca"], is_tls=False, can_sign=True)
    create_ca(org["tlsca"], is_tls=True, can_sign=True)

     # "admins" must be first
    roles = ["admins", "users", "orderers", "peers"]
    for role in roles:
        if role == roles[1]:
            copy_admincerts_to_admins(org)
        if role in org and org[role]:
            is_admin = False
            for element in org[role]:
                create_docker(role, element, org)
                elem_domain = element["Hostname"] + "." + org['Domain']
                subfolder = role
                attributes = ""
                if role == "admins":
                    subfolder = "users"
                    is_admin = True
                    add_admin_to_explorer(org, element)
                elif role == "peers":
                    add_peer_to_explorer(org, element)
                elif role == "users" and "Attributes" in element and element['Attributes']:
                    attr_values = ["\\\""+k+"\\\":"+"\\\""+str(v)+"\\\"" for k, v in element["Attributes"].iteritems()]
                    attributes = ",".join(attr_values)

                subfolder = subfolder + "/" + elem_domain
                create_ca({'Parent':org["ca"], 'Domain':org["Domain"]}, is_tls=False, can_sign=False, subfolder=subfolder, attributes=attributes, is_admin=is_admin)
                create_ca({'Parent':org["tlsca"], 'Domain':org["Domain"]}, is_tls=True, can_sign=False, subfolder=subfolder, attributes=attributes, is_admin=is_admin)

def getSuffix(domain, subfolder):
    if subfolder == "":
        return domain
    return subfolder.split('/')[-1]

def create_combined_ca(caconf, is_tls=False, subfolder=""):
    """Creates a combined certificate"""
    tls = "tls" if is_tls else ""
    # Fetch the list of certificate paths up to root

    output = CRYPTO_CONFIG_PATH + caconf["Domain"] + "/" + subfolder + "/" + tls + "ca.combined." + getSuffix(caconf["Domain"], subfolder) + "-cert.pem"
    paths = []
    while "Parent" in caconf:
        ca_file = CRYPTO_CONFIG_PATH + caconf["Domain"] + "/" + subfolder + "/" + tls + "ca/" + tls + "ca." + getSuffix(caconf["Domain"], subfolder) + "-cert.pem"
        paths.append(ca_file)
        subfolder = "" # Override subfolder
        caconf = caconf["Parent"]

    # We're at the root, so add it to the array as well
    ca_file = CRYPTO_CONFIG_PATH + caconf["Domain"] + "/" + subfolder + "/" + tls + "ca/" + tls + "ca." + getSuffix(caconf["Domain"], subfolder) + "-cert.pem"
    paths.append(ca_file)


    reversed_paths = list(reversed(paths)) # First element is root
    # Create the combined file:
    call(
        "cat",
        ' '.join(reversed_paths),
        "> " + output)

    return reversed_paths

def create_ca(caconf, is_tls=False, subfolder="", docker=False, can_sign=False, attributes="", is_admin=False):
    """Creates a ca in caconf["Domain"]/subfolder/(tls)ca"""
    tls = "tls" if is_tls else ""
    ca_folder = CRYPTO_CONFIG_PATH + caconf["Domain"] + "/" + subfolder + "/" + tls + "ca"
    # Create ca root
    call("mkdir", "-p", ca_folder)
    global ORG_MSP_CHANGED

    if "Parent" in caconf:
        # Intermediate CA
        parent_domain = caconf["Parent"]["Domain"]
        parent_path = CRYPTO_CONFIG_PATH + parent_domain + "/" + tls + "ca/" + tls  + "ca." + parent_domain
        attr_list = "\"{\\\"attrs\\\":{"+attributes+"}}\""
        ca_cn = tls+"ca."+getSuffix(caconf["Domain"], subfolder)
        ca_filename = ca_folder + '/' + ca_cn + '-cert.pem'
        if OVERRIDE or not os.path.isfile(ca_filename):
            call(
                to_pwd("create_intermediate_ca.sh"),
                ca_cn,
                ca_folder,
                parent_path,
                tls+"ca",
                str(can_sign),
                attr_list)
            ORG_MSP_CHANGED = ORG_MSP_CHANGED or is_admin or subfolder == ""
    else:
        # Root CA
        ca_cn = tls+"ca."+caconf["Domain"]
        ca_filename = ca_folder + '/' + ca_cn + '-cert.pem'
        if OVERRIDE or not os.path.isfile(ca_filename):
            call(to_pwd("create_root_ca.sh"), ca_cn, ca_folder, tls+"ca")
            ORG_MSP_CHANGED = ORG_MSP_CHANGED or is_admin or subfolder == ""
    ca_paths = create_combined_ca(caconf, is_tls, subfolder)

    if docker:
        create_docker("ca", caconf, None)
    else:
        create_msp(caconf["Domain"], ca_paths, is_tls, subfolder, is_admin)

with open(YAML_CONFIG, 'r') as stream:
    try:
        CONF = yaml.load(stream)
        CRYPTO_CONFIG_PATH = GEN_PATH + "/crypto-config/"

        call("mkdir -p", CRYPTO_CONFIG_PATH)

        for init_ca in CONF["PREGEN_CAs"]:
            create_ca(init_ca["ca"], is_tls=False, docker=True, can_sign=True)
            ca_path = CRYPTO_CONFIG_PATH + init_ca["ca"]["Domain"]
            if OVERRIDE or not os.path.isdir(ca_path + '/tlsca'):
                call('rm -rfd ', ca_path + '/tlsca')
                call("cp -r", ca_path + "/ca", ca_path + "/tlsca")
                call("mv", ca_path + "/tlsca/ca." + init_ca["ca"]["Domain"] + "-cert.pem",
                     ca_path + "/tlsca/tlsca." + init_ca["ca"]["Domain"] + "-cert.pem"
                    )

                call("mv", ca_path + "/tlsca/ca." + init_ca["ca"]["Domain"] + "-key.pem",
                     ca_path + "/tlsca/tlsca." + init_ca["ca"]["Domain"] + "-key.pem"
                    )
                create_combined_ca(init_ca["ca"], is_tls=True)

        for theOrg in CONF["Orgs"]:
            if 'peers' in theOrg and theOrg['peers']:
                ORG_MAP['currentId'] += 1
                ORG_MAP[theOrg["Domain"]] = {
                    'id': ORG_MAP['currentId'],
                    'peers': {
                        'currentId': 0
                    }
                }
                EXPLORER_DATA_PROD['network-config'][get_org_nb(theOrg)] = {}
            create_all_msp(theOrg)

        if ORG_MSP_CHANGED:
            print 'Generating channel artifacts...'

            call(to_pwd('../fabric_artifacts/gen_configtx.py'), YAML_CONFIG, CONFIGTX_BASE)
            call('mkdir -p', GEN_PATH + '/scripts')
            with open(GEN_PATH + '/scripts/explorer-config.prod.json', 'w+') as stream:
                EXPLORER_DATA_PROD['channel'] = CONF['Channels'][0]['Name']
                stream.write(json.dumps(EXPLORER_DATA_PROD,sort_keys=True,indent=2))
            with open(GEN_PATH + '/scripts/explorer-config.dev.json', 'w+') as stream:
                dev_org = CONF['Devmode']
                EXPLORER_DATA_DEV['channel'] = CONF['Channels'][0]['Name']
                EXPLORER_DATA_DEV['network-config']['org1'] = {}
                add_admin_to_explorer(dev_org, dev_org['admins'][0], True)
                add_peer_to_explorer(dev_org, dev_org['peers'][0], True)

                stream.write(json.dumps(EXPLORER_DATA_DEV,sort_keys=True,indent=2))
        else:
            print "Organisation MSP did not change, not regenerating channel artifacts"

    except yaml.YAMLError as exc:
        print exc
