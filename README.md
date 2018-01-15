# Install:

Install the dependencies:
* Git
* [Python](https://www.python.org/downloads/) modules:
    * [pyaml](https://github.com/yaml/pyyaml)
* [Vagrant](https://www.vagrantup.com/docs/installation/) plugins (for running the network on AWS):
    * vagrant-aws
    * vagrant-docker-compose
* [NPM](https://docs.npmjs.com/getting-started/installing-node)
* [aws](https://aws.amazon.com/cli/) command line with the region and keys configured (run `aws configure`)
* Environment variables
   * AWS_SECRET_ACCESS_KEY=your aws secret key
   * AWS_ACCESS_KEY_ID=your aws access key id

Run the following command from your terminal:

    curl -fsSL https://raw.githubusercontent.com/Kunstmaan/hyperledger-fabric-network-setup/master/scripts/install.sh?token=AG6ftlJwD7jEr7kZph_QEsqncTTeroBFks5aZc1pwA%3D%3D | bash

# Scripts:

---
#### Environment variables description:
* `GEN_PATH`: The path to the folder that should contain crypto-config, docker files and channel artifacts

---

* `scripts/hyperledgerNetworkTool.py`
    > Master script that uses all others. Run it with -h to have help on how to use it. This is normally the only script you should run.

* `scripts/crypto_tools/cryptogen.py`
    > Creates crypto-config structure containing the MSP for all organisations, users and peers. Also creates the docker files and runs fabric_artifacts/gen_configtx. Uses all other scripts in `scripts/crypto_tools`, which use openssl.
    Uses TLS handshakes.

* `scripts/fabric_artifacts/gen_configtx.py`
    > Creates the scripts that generate channel artifacts. Requires the files created by cryptogen.py

* `scripts/create-remote_scripts.py`
    > Creates scripts that automatically connect to the network in order to install channels or update chaincodes

* `scripts/get_hosts_scripts.py`
    > Creates scripts that modify /etc/hosts in order to resolve network names to ip addresses


The shared folder is shared to all hyperledger tools (CLI) docker containers. It will also be synced to all aws nodes

The `shared/chaincode_tools/` folder contains code intended to run on the tools docker containers
* `shared/chaincode_tools/update_chaincodes.py`
    > Pulls code from the git repository, reads the config file and installs/instantiates/upgrades chaincodes according to that

* `shared/chaincode_tools/compile_chaincode.sh`
    > Compiles go chaincode

* `shared/chaincode_tools/pull_chaincode.sh`
    > Pulls the chaincode repository and puts it in $GOPATH/src. Used by update_chaincodes.py. Uses keys defined in aws_config in fields `private_ssh_key_for_chaincode_repo` and `public_ssh_key_for_chaincode_repo`

* `provisioning/install.sh`
    > installs node, go and the hyperledger tools. Not used anymore, you can use it manually on AWS nodes however.

* `provisioning/stopDocker.sh`
    > Stops all docker containers

* `provisioning/install_fabric_tools.sh`
    > installs `configtxgen`, `configtxlator`, `cryptogen`, `orderer`, `peer`

## Structure of the generated folder

This folder is created by running `scripts/hyperledgerNetworkTool.py gen`

It contains 6 folders (the sixth is generated when booting the network):
* channel
    > Contains scripts that allow the creation of channel artifacts and their
    use in creating and joining channels.

    * `$GEN_PATH/channel/create_and_join_channel.sh`
    > Creates the channel, and installs it on the relevant peers

    * `$GEN_PATH/channel/create_channel_artifacts.sh`
    > Creates the initial orderer blocks and initial transactions for each channel

* crypto_config
    > Contains all the cryptographic material needed by a hyperledger fabric network.

* devmode
    > Contains a simplified version of the network that can be used to develop chaincode easily.
    This repository can be used to develop javascript chaincode efficiently: [hyperledger-fabric-chaincode-dev-setup](https://github.com/janb87/hyperledger-fabric-chaincode-dev-setup)

* docker
    > Contains the docker files used to boot the network

* hfc-key-store
    > Contains signing identities required to connect to the blockchain via an app

* scripts
    > Contains scripts that you can run on your local machine to update /etc/hosts file


# Cryptographic materials
------
## Certificate settings

Signature Algorithm must be *ecdsa-with-SHA1*
> The settings are given in the form CA - TLS

| Property                          | Root  | Inter | Org   | Peer  | User  |
| --------------------------------- |:-----:|:-----:|:-----:|:-----:|:-----:|
| X509v3 Key Usage                  |       |       |       |       |       |
| --- Digital Signature             | V - V | V - V | V - V | V - V | V - V |
| --- Key Encipherment              | V - V | V - V | V - V | X - V | X - V |
| --- CRL Sign                      | V - V | V - V | V - V | X - X | X - X |
| --- Certificate Sign              | V - V | V - V | V - V | X - X | X - X |
| X509v3 Basic Constraints          |       |       |       |       |       |
| --- CA:TRUE                       | V - V | V - V | V - V | X - X | X - X |
| --- CA:FALSE                      | X - X | X - X | X - X | V - V | V - V |
| X509v3 Authority Key Identifier   | X - X | V - V | V - V | V - V | V - V |
| X509v3 Subject Key Identifier     | V - V | V - V | V - V | V - V | V - V |
| X509v3 Extended Key Usage         |       |       |       |       |       |
| --- TLS Web Server Authentication | X - X | X - X | X - V | X - V | X - V |
| --- TLS Web Client Authentication | X - X | X - X | X - V | X - V | X - V |
| --- 2.5.29.37.0                   | V - V | V - V | V - X | X - X | X - X |


# AWS Configuration
* Key Pair:
  > You need a key pair which will be used to connect to the aws instances. This key
    pair consists of a public key (that is on aws), a private key (that is on your local machine) and a
    key pair name used to refer to that key when creating the instances
    
# Roadmap
* Install dependencies automatically
* trigger aws configure automatically
* make BatchSize, BatchTimeout, ... more configurable
