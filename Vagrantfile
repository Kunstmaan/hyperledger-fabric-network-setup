#!/usr/bin/env ruby
# This Vagrantfile is a good example of provisioning multiple EC2 instances
# using a single file.
# http://stackoverflow.com/questions/24385079/multiple-ec2-instances-using-vagrant
# read aws specific config from json file
# https://github.com/savishy/docker-examples/tree/master/docker-swarm/docker-swarm-aws

# https://hub.docker.com/r/consul/
# https://luppeng.wordpress.com/2016/05/03/setting-up-an-overlay-network-on-docker-without-swarm/
# plugins : vagrant plugin install vagrant-docker-compose
# plugins : vagrant plugin install vagrant-aws

# NOTE: The consul master must be the first instance in aws.json
# (it must boot before the others)

require 'yaml'

Vagrant.require_version '>= 2.0.0'

INSTALL_DIR = File.expand_path(File.dirname(__FILE__))
VERSION_FILE = "#{INSTALL_DIR}/.HLVersion".freeze

def inc_version
  unless File.file?(VERSION_FILE)
    File.open(VERSION_FILE, 'w') { |file| file.write('1') }
  end

  file = File.open(VERSION_FILE, File::RDWR)
  file.seek(0) # rewind to the beginning of the file

  version = file.readline.to_i.freeze

  file.seek(0)
  file.write(version + 1) # Increment version number
  file.close
  version
end

# Version tag to easily find instances in aws console
VERSION = inc_version

AWS_CFG = JSON.parse(File.read(ENV['AWS_CONFIG'])).freeze

# Set secret access key in your environment
SECRET_ACCESS_KEY = ENV['AWS_SECRET_ACCESS_KEY'].freeze
ACCESS_KEY_ID = ENV['AWS_ACCESS_KEY_ID'].freeze
KEYPAIR_NAME = AWS_CFG['keypair_name'].freeze
SECURITY_GROUPS = AWS_CFG['security_groups'].freeze
PRIVATE_KEY_PATH = AWS_CFG['private_key_path'].freeze

GEN_PATH = ENV['GEN_PATH'].freeze
SHARED_PATH = "#{INSTALL_DIR}/shared/".freeze
HYPERLEDGER_VERSION = '1.1.0'.freeze
DOCKER0_IP_ADDRESS = '172.17.0.1'.freeze
CONSUL_MASTER_IP = AWS_CFG['consul_master_ip'].freeze

DOCKER_COMPOSE_VERSION = '1.17.0'.freeze
CONSUL_VERSION = '1.0.0'.freeze

CMD_GET_PUBLIC_IP = 'dig +short myip.opendns.com @resolver1.opendns.com'.freeze

def docker_opts(private_ip_address)
  # NOTE: Listen only on the private ip, and not on any ip (0.0.0.0).
  # Otherwise chinese coin miners will connect to the dameon and mine bitcoins..
  # If this dameon needs to listen on a public ip,
  # should secure connection with certificates and use port 2376 (and not 2375)

  "DOCKER_OPTS=\"-H tcp://#{private_ip_address}:2375 -H unix:///var/run/docker.sock --cluster-advertise eth0:2375 --cluster-store consul://#{CONSUL_MASTER_IP}:8500\""
end

NETWORK_NAME = 'hyperledgerNet'.freeze

WAIT_FOR_NETWORK = ''"while ! docker network ls | grep -q #{NETWORK_NAME};
                      do echo \"Waiting for #{NETWORK_NAME}...\";
                        sleep 5;
                      done;
                      sleep 10;
                      echo \"Connected to #{NETWORK_NAME} !\""''.freeze

def wait_for_port(ip_address, port)
  ''"while ! nc -zv -w5 #{ip_address} #{port};
     do echo \"Waiting for #{ip_address}:#{port} to be open\";
       sleep 5;
     done;
     sleep 10;
     echo \"#{ip_address}:#{port} is now open !\";
  "''
end

def get_docker_daemon_cmd(private_ip_address, wait = true)
  (wait ? wait_for_port(CONSUL_MASTER_IP, 8500) : '') + ''"
    echo 'Configuring docker daemon...'
    sed -i '/DOCKER_OPTS=/d' /etc/default/docker
    echo '#{docker_opts(private_ip_address)}' >> /etc/default/docker
    echo '--> Modifying docker.service...'
    cp /vagrant/shared/docker.service /lib/systemd/system/docker.service
    echo '--> Reloading daemon settings...'
    systemctl daemon-reload
    echo '--> Restarting docker service...'
    service docker restart
    echo 'Done. Docker dameon configured.'
  "''
end

def get_docker_consul_args(private_ip_address)
  ''"-d \
  -v /mnt:/data \
  -p #{private_ip_address}:8300:8300 \
  -p #{private_ip_address}:8301:8301 \
  -p #{private_ip_address}:8301:8301/udp \
  -p #{private_ip_address}:8302:8302 \
  -p #{private_ip_address}:8302:8302/udp \
  -p #{private_ip_address}:8400:8400 \
  -p #{private_ip_address}:8500:8500 \
  -p #{DOCKER0_IP_ADDRESS}:53:53/udp \
  --net=host"''
end

# Configures an AWS instance
# Params:
# +aws_node+:: the config of vagrant
# +private_ip_address+:: the private ip address of the AWS node
# +node_name+:: the name of the node, will be shown in AWS
# +node_config+:: json node configuration
def configure_instance(aws_node, private_ip_address, node_name, node_config)
  # Spin up EC2 instances
  aws_node.vm.provider :aws do |ec2, override|
    ec2.keypair_name = KEYPAIR_NAME
    ec2.access_key_id = ACCESS_KEY_ID
    ec2.secret_access_key = SECRET_ACCESS_KEY
    ec2.security_groups = SECURITY_GROUPS
    override.ssh.private_key_path = PRIVATE_KEY_PATH

    # read region, ami etc from json.
    ec2.region = AWS_CFG['region']
    ec2.subnet_id = AWS_CFG['subnet_id']
    ec2.availability_zone = AWS_CFG['region'] + AWS_CFG['availability_zone']
    ec2.ami = node_config['ami_id']
    ec2.instance_type = node_config['instance_type']
    ec2.private_ip_address = private_ip_address
    ec2.associate_public_ip = true

    if node_config.key?('volume_size')
      # Size in GB
      # (untested)
      ec2.block_device_mapping = [{ 'DeviceName' => '/dev/sda1', 'Ebs.VolumeSize' => node_config['volume_size'] }]
    end

    override.ssh.username = AWS_CFG['ssh_username']

    # Collect tags (can't be longer than 250 chars)
    ec2.tags = ({})
    ec2.tags['Name'] = node_name[0..245]
    ec2.tags['Type'] = 'Hyperledger'
    ec2.tags['Version'] = VERSION
    ec2.tags['Fabric'] = node_config['fabric'].map { |f| f['role'] }.join(',')[0..245]
  end
end

def configure_consul(aws_node, node_name, private_ip_address)
  # Consul UI is NOT secured ! To do so, you must configure an ACL
  docker_consul_args = get_docker_consul_args(private_ip_address)
  consul_cmd = "agent -server -advertise #{private_ip_address} -client=#{private_ip_address}"
  aws_node.vm.provision 'docker' do |d|
    is_consul_master = private_ip_address == CONSUL_MASTER_IP
    d.pull_images "consul:#{CONSUL_VERSION}"
    d.post_install_provision 'shell', inline: get_docker_daemon_cmd(private_ip_address, !is_consul_master)
    if is_consul_master
      # Assume there is only one consul master
      d.run 'consul', args: docker_consul_args + " -h consul_master_#{node_name}", cmd: consul_cmd + ' -bootstrap -ui'
      aws_node.vm.provision 'shell', inline: "sleep 10; docker network create --driver overlay --subnet=192.168.100.0/24 #{NETWORK_NAME}"
      aws_node.vm.provision 'shell', inline: "publicIP=\"$(#{CMD_GET_PUBLIC_IP})\";echo \"Consul UI available at: $publicIP:8500\""
    else
      d.run 'consul', args: docker_consul_args + " -h consul_#{node_name}", cmd: consul_cmd + " -join #{CONSUL_MASTER_IP}"
    end
  end
end

# Configures an orderer, ca or peer node
# Params:
# +aws_node+:: aws node configuration
# +node_config+:: json node configuration
def configure_fabric(aws_node, node_config)
  aws_node.vm.synced_folder "#{GEN_PATH}/channel/", '/vagrant/channel', type: 'rsync'
  aws_node.vm.synced_folder "#{GEN_PATH}/crypto-config/", '/vagrant/crypto-config', type: 'rsync'
  node_config['fabric'].each do |fabric|
    role = fabric['role']
    docker_yaml = fabric['docker']
    couchdb_port = fabric['couchdb_port']
    aws_node.vm.provision 'docker' do |d|
      d.pull_images "hyperledger/fabric-#{role}:x86_64-#{HYPERLEDGER_VERSION}"
      if role == 'peer'
        # Download and run couchdb
        d.pull_images 'yeasy/hyperledger-fabric-couchdb'
        # TODO: In future, couchdb should not publish port
        # but only expose them for incresed security,
        # and peer containers should link to couchdb
        d.run 'yeasy/hyperledger-fabric-couchdb', args: "-e COUCHDB_PASSWORD=password -e COUCHDB_USER=admin -p #{couchdb_port}:5984"
        # Pre-load fabric image for chaincode instantiation
        d.pull_images "hyperledger/fabric-ccenv:x86_64-#{HYPERLEDGER_VERSION}"
      end
    end

    if role == 'peer'
      aws_node.vm.provision 'shell', inline: "docker tag hyperledger/fabric-ccenv:x86_64-#{HYPERLEDGER_VERSION} hyperledger/fabric-ccenv"
      # wait for couchdb
      aws_node.vm.provision 'shell', inline: wait_for_port('0.0.0.0', couchdb_port)
    end

    # Remove version tag on the image by tagging it
    aws_node.vm.provision 'shell', inline: "docker tag hyperledger/fabric-#{role}:x86_64-#{HYPERLEDGER_VERSION} hyperledger/fabric-#{role}"

    # wait until network is up
    aws_node.vm.provision 'shell', inline: WAIT_FOR_NETWORK

    docker_compose_file_name = "/vagrant/docker/#{docker_yaml}"
    aws_node.vm.provision :docker_compose, yml: docker_compose_file_name, options: '', compose_version: DOCKER_COMPOSE_VERSION
  end
end

def configure_ssh(aws_node)
  # Don't link directly to .ssh because it will hide the original .ssh folder,
  # which contains the authorized_keys files needed to log in via ssh.
  # Can't move files directly to folders that need elevated privileges,
  # because the file uploads by the file provisioner are done as the SSH
  # or PowerShell user. So we move them afterwards.
  aws_node.vm.provision 'file', source: AWS_CFG['public_ssh_key_for_chaincode_repo'], destination: '~/id_rsa.pub'
  aws_node.vm.provision 'file', source: AWS_CFG['private_ssh_key_for_chaincode_repo'], destination: '~/id_rsa'
  aws_node.vm.provision 'shell', path: 'scripts/provisioning/configure_ssh.sh', args: [AWS_CFG['ssh_username']]
end

def sync_other_files(aws_node, node_config)
  return unless node_config.key?('files_to_sync')
  node_config['files_to_sync'].each do |f|
    aws_node.vm.provision 'file', source: f[0], destination: f[1]
  end
end

# start vagrant configuration
Vagrant.configure(2) do |config|
  config.vm.box = 'dummy'
  config.vm.box_url = 'https://github.com/mitchellh/vagrant-aws/raw/master/dummy.box'

  # loop through each of 'ec2s' key
  AWS_CFG['ec2s'].each do |node|
    node_name = 'HLF_' + node[0]
    node_config = node[1] # The node data
    private_ip_address = node_config['ip']

    # Node specific configuration
    config.vm.define node_name do |aws_node|
      aws_node.nfs.functional = false
      # Prevent Vagrant from mounting the default /vagrant synced folder
      config.vm.synced_folder '.', '/vagrant', disabled: true
      configure_instance(aws_node, private_ip_address, node_name, node_config)
      configure_ssh(aws_node)
      sync_other_files(aws_node, node_config)
      aws_node.vm.provision 'shell', inline: 'apt-get -y update'
      aws_node.vm.provision 'install', type: :shell, path: 'scripts/provisioning/stopDocker.sh'
      aws_node.vm.synced_folder SHARED_PATH, '/vagrant/shared', type: 'rsync'
      aws_node.vm.synced_folder "#{GEN_PATH}/docker/", '/vagrant/docker', type: 'rsync'
      configure_consul(aws_node, node_name, private_ip_address)
      configure_fabric(aws_node, node_config)
    end
    # config.vm.define node_name
  end
  # aws_cfg['ec2s']
end
