# Install:

Install the dependencies:
* Git
* [Python](https://www.python.org/downloads/) modules:
    * [pyaml](https://github.com/yaml/pyyaml)
* [Vagrant](https://www.vagrantup.com/docs/installation/) plugins (for running the network on AWS):
    * vagrant-aws
    * vagrant-docker-compose
* [NPM](https://docs.npmjs.com/getting-started/installing-node)
* [aws](https://aws.amazon.com/cli/)

Run the following command from your terminal:

```
curl -fsSL https://raw.githubusercontent.com/Kunstmaan/hyperledger-fabric-network-setup/master/scripts/install.sh?token=AG6ftlJwD7jEr7kZph_QEsqncTTeroBFks5aZc1pwA%3D%3D | bash
```

This repo depends on the fact that the chaincode repo you want to deploy has at least the chaincodes configuration in your package.json
https://github.com/Kunstmaan/hyperledger-fabric-chaincode-dev-setup#initializing-new-project

# Commands

With the following command you can get an overview of all the commands available:

```
kuma-hf-network -h
```

## Boostrap a default network configuration

When you want to create a new network configuration, you can initialize a new network with the following command:

```
kuma-hf-network boostrap .
```

This will create a default aws configuration and network configuration at the provided path and generate all the artifacts based on this configuration.

## Generate certificates, docker files, channel artifacts

```
kuma-hf-network generate <crypto_config>
```

Generates all the artifacts needed to bring the network up and configure the channels based on the provided `crypto_config`.

## Generate a new user for a certain organisation

```
kuma-hf-network generate-user <name> <org> <crypto_config>
```

Generate al the crytographic material for a new user belonging to a certain organisation.

Generates all the artifacts needed to bring the network up and configure the channels based on the provided `crypto_config`.

## Bring the network UP

```
kuma-hf-network network-up <crypto_config> <aws_config>
```

Create all the aws instances as provided in the `aws_config` and bring up all the fabric instances using the cryptographic material generated with the `crypto_config`. This will also output scripts for updating the hosts file with the DNS linking to the ip addresses on aws.

## Bring the network DOWN

```
kuma-hf-network network-down <aws_config>
```

Bring the network back down.

## Update the chaincodes on the current network

```
kuma-hf-network update-chaincodes
```

Upgrade the chaincodes on the network based on the version in the `package.json` of each chaincode. This script depends on the chaincodes being generated with the [hyperledger-fabric-chaincode-dev-setup](https://github.com/Kunstmaan/hyperledger-fabric-chaincode-dev-setup).

## Update the current tool

```
kuma-hf-network update
```

Update the script to the latest version.

# AWS Configuration

In the back we are using the aws cli utility, make sure this is configured correctly by running `aws configure`. And setting the following environment variables: 
   * `AWS_SECRET_ACCESS_KEY`, your aws secret key
   * `AWS_ACCESS_KEY_ID`, your aws access key id

More information can be found here:
https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html

## Configuring your AWS EC2 Instances

First you need to configure your AWS account, make sure a VPC is created with a keypair to access it, it's own subnet and security-group. A detailed tutorial can be found [here](https://docs.aws.amazon.com/AmazonVPC/latest/UserGuide/VPC_Internet_Gateway.html). When this is all configured you can start modifying the configuration file so that this script can bring the network up. Configuring the network can be done via the [aws configuration file](./configuration/aws-example.json). This is the configuration file you need to provide when running `kuma-hf-network network-up`.

* `region`, the region to start the instances in, for example "eu-west-1"
* `availability_zone`, the availability zone within the region to launch the instance. If nil, it will use the default set by Amazon.
* `security_groups`, an array of security group ids, more information can be found [here](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-network-security.html)
* `subnet_id`, the id of the subnet to use, more information can be found [here](https://docs.aws.amazon.com/AmazonVPC/latest/UserGuide/VPC_Subnets.html)
* `keypair_name`, the name of the keypair that should be used to access the EC2 Instance, more information can be found [here](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html)
* `private_key_path`, the path on your local machine to the private key of the keypair
* `ssh_username`, the name of the user to access the EC2 instance
* `consul_master_ip`, the ip address of the instance you want to use as consul master
* `chaincode_repository`, the gitrepository where the chaincode can be found
* `chaincode_base_path`, the path to the chaincode inside the chaincode github repository
* `chaincode_build`, specify if the chaincode should be build first, this will execute "npm run build"
* `private_ssh_key_for_chaincode_repo`, the path to the private key needed to get access to to the chaincode repository
* `public_ssh_key_for_chaincode_repo`, the path to the public key needed to get access to to the chaincode repository
* `ec2s`, a map of all the ec2 instances you cant to deploy, with the key being the name and the value being instance specific configuration

### EC2 Instance configuration

You can create as many of ec2 instances as you want, for every instance you need to configure the following things:

* `ami_id`, the ami id to boot, for example: ami-785db401 which is an amd64 ubuntu server
* `instance_type`: the type of instance
* `fabric`: an array with the different fabric tools you want to deploy on this instance. Each tool exists out of the role (possible roles are "orderer", "peer" and "tools") and the docker file to use.
* `ip`: the ip address for this instance
* `volume_size`: the volume size for the ebs instance in GB

# An overview of the indiviual scripts:
---

Environment variables description:
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

# Structure of the generated folder

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
