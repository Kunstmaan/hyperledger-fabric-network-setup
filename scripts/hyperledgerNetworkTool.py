#!/usr/bin/env python2

"""
    hyperledgerNetworkTool -h

    Main tool for creation of hyperledger network artifacts,
    and for the creating of the network on AWS
"""

import os
import sys
from argparse import ArgumentParser
from argparse import RawTextHelpFormatter

DEBUG = False
PWD = os.path.dirname(__file__)

def to_pwd(script):
    """Converts the script path to the correct path"""
    return PWD + "/" + script

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
        fail("ERROR: An error occured while executing " + cmd + ". See above for details.")

def install_fabric_tools():
    print "Installing fabric tools..."
    call(to_pwd('provisioning/install_fabric_tools.sh'))
    print "Done"

def gen_cryptographic_material(parsed_args):
    crypto_config = parsed_args.crypto_config
    gen_path = os.path.abspath(parsed_args.gen_path)
    install_fabric_tools()
    if not args.noOverride:
        print "Cleaning pre-existing generated files..."
        call('rm -rfd {0}'.format(gen_path))
        call('mkdir -p {0}'.format(gen_path))
    print "Generating cryptographic material..."
    call('export GEN_PATH={0} &&'.format(gen_path), to_pwd('crypto_tools/cryptogen.py'), crypto_config, str(not args.noOverride))
    # This also generates the channel artifacts, if changes were made.
    print "Done"

def gen_channel_artifacts(parsed_args):
    """Forces generation of channel artifacts"""
    crypto_config = parsed_args.crypto_config
    gen_path = os.path.abspath(parsed_args.gen_path)
    install_fabric_tools()
    print "Generating channel artifacts..."
    call('export GEN_PATH={0} &&'.format(gen_path), to_pwd('fabric_artifacts/gen_configtx.py'), crypto_config)
    print "Done"


def network_down(parsed_args):
    aws_config = os.path.abspath(parsed_args.aws_config)
    gen_path = os.path.abspath(parsed_args.gen_path)
    print 'May ask sudo password at this point to clean /etc/hosts file of previously created entries. If you never brought the network up, this won\'t make any changes'
    clean_hosts = gen_path + '/scripts/clean_hosts.sh'
    if os.path.isfile(clean_hosts):
        call(clean_hosts)
    call('export AWS_CONFIG={0} && export GEN_PATH={1} && pushd {2} && vagrant destroy -f && popd'.format(aws_config, gen_path, PWD))

def network_up(parsed_args):
    crypto_config = os.path.abspath(parsed_args.crypto_config)
    aws_config = os.path.abspath(parsed_args.aws_config)
    gen_path = os.path.abspath(parsed_args.gen_path)
    print 'May ask sudo password at this point to edit /etc/hosts file with the names of the nodes, to be able to resolve them to public ips.'
    call('export GEN_PATH={0} &&'.format(gen_path), to_pwd('get_hosts_scripts.py'), aws_config, 'False') # To get the private ips
    call('export AWS_CONFIG={0} && export GEN_PATH={1} && pushd {2} && vagrant up && popd'.format(aws_config, gen_path, PWD))
    call('export GEN_PATH={0} &&'.format(gen_path), to_pwd('get_hosts_scripts.py'), aws_config, 'True') # To get the public ips
    call('export GEN_PATH={0} &&'.format(gen_path), to_pwd('create_remote_scripts.py'), crypto_config, aws_config)
    call(gen_path + '/scripts/set_hosts_public.sh')
    call(gen_path + '/scripts/create_and_join_channels_remote.sh')
    call(gen_path + '/scripts/update_remote_chaincodes.sh')


def update_chaincodes(parsed_args):
    gen_path = os.path.abspath(parsed_args.gen_path)

    call(gen_path + '/scripts/update_remote_chaincodes.sh')

def update_apps(parsed_args):
    print """ANB ONLY: Make sure you commited the generated files to the git,
especially generated/scripts/set_hosts_private.sh !"""
    gen_path = os.path.abspath(parsed_args.gen_path)

    call(gen_path + '/scripts/update_remote_apps.sh')




parser = ArgumentParser(description="""This tool allows you to create a certificate structure for hyperledger fabric,
and then to use that structure to boot a multinode network on Amazon Web Services.
Once the network is running, this tool also allows you to remotely upgrade
chaincode running on the network.
""", formatter_class=RawTextHelpFormatter)
subparsers = parser.add_subparsers()

parser_gen = subparsers.add_parser('gen', help="""generate certificate structure, initial channel blocks,
hyperledger fabric artifacts and docker configurations.""")
parser_gen.add_argument('crypto_config', type=str, help='cryptographic configuration of the network, as YAML file. See the provided example for details.')
parser_gen.add_argument('gen_path', nargs='?', type=str, help='Where the generated files should be saved (default: ./generated)', default='./generated')
parser_gen.add_argument('--noOverride', help='Do not override existing files (default: false). Useful if you want to add more users. If this is not set, will delete the generated folder and generate everything from scratch', action='store_true')
parser_gen.set_defaults(func=gen_cryptographic_material)

parser_up = subparsers.add_parser('up', help="""Bring the network up. Requires the artifacts to be generated
     does:
         * vagrant up
         * modifies /etc/hosts to resolve hostnames
         * installs hyperledger fabric channels
         * installs first version of chaincode""")
parser_up.add_argument('crypto_config', type=str, help='cryptographic configuration of the network, as YAML file.')
parser_up.add_argument('aws_config', type=str, help='AWS network configuration, as JSON file.')
parser_up.add_argument('gen_path', nargs='?', type=str, help='Where the generated files are (default: ./generated)', default='./generated')
parser_up.set_defaults(func=network_up)

parser_down = subparsers.add_parser('down', help="""Bring the network down.
     does:
         * vagrant destroy -f
         * cleans /etc/hosts""")
parser_down.add_argument('aws_config', type=str, help='AWS network configuration, as JSON file.')
parser_down.add_argument('gen_path', nargs='?', type=str, help='Where the generated files are (default: ./generated)', default='./generated')
parser_down.set_defaults(func=network_down)

parser_update_chaincodes = subparsers.add_parser('updateChaincodes', help='Updates chaincodes on the network. Only run this if the network is up')
parser_update_chaincodes.add_argument('gen_path', nargs='?', type=str, help='Where the generated files are (default: ./generated)', default='./generated')
parser_update_chaincodes.set_defaults(func=update_chaincodes)

parser_update_apps = subparsers.add_parser('updateApps', help='Updates apps on the network. Only run this if the network is up')
parser_update_apps.add_argument('gen_path', nargs='?', type=str, help='Where the generated files are (default: ./generated)', default='./generated')
parser_update_apps.set_defaults(func=update_apps)

parser_channel = subparsers.add_parser('genChannelArtifacts', help="""Generate channel artifacts. This is run by the gen
command and should not be run manually unless you made manual
changes to the generated folder, which requires new channel
artifacts to be generated.""")
parser_channel.add_argument('crypto_config', type=str, help='cryptographic configuration of the network, as YAML file. See the provided example for details.')
parser_channel.add_argument('gen_path', nargs='?', type=str, help='Where the generated files should be saved (default: ./generated)', default='./generated')
parser_channel.set_defaults(func=gen_channel_artifacts)


args = parser.parse_args()
args.func(args)
