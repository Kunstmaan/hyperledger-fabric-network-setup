#!/bin/bash
# Created by Guillaume Leurquin, guillaume.leurquin@accenture.com

set -eu

echo "Configuring ssh..."

CURRENTUSER=$1
echo "CURRENTUSER=$CURRENTUSER"


echo "Creating /vagrant/ssh folder"
mkdir -p /vagrant/ssh

echo "Moving private key to /vagrant/ssh/id_rsa"
mv /home/$CURRENTUSER/id_rsa /vagrant/ssh/id_rsa
ln -s /vagrant/ssh/id_rsa /home/$CURRENTUSER/.ssh/id_rsa
echo "Changing permissions of private key"
chown $CURRENTUSER /home/$CURRENTUSER/.ssh/id_rsa
chmod 600 /home/$CURRENTUSER/.ssh/id_rsa
echo "Contents of /vagrant/ssh:"
ls /vagrant/ssh
echo "Contents of /home/$CURRENTUSER/.ssh:"
ls /home/$CURRENTUSER/.ssh
echo "Contents of /home/$CURRENTUSER:"
ls /home/$CURRENTUSER
echo "Done with private key"

echo "Moving public key to /vagrant/ssh/id_rsa"
mv /home/$CURRENTUSER/id_rsa.pub /vagrant/ssh/id_rsa.pub
ln -s /vagrant/ssh/id_rsa.pub /home/$CURRENTUSER/.ssh/id_rsa.pub

echo "Changing permissions of public key"
chown $CURRENTUSER /home/$CURRENTUSER/.ssh/id_rsa.pub
chmod 644 /home/$CURRENTUSER/.ssh/id_rsa.pub
echo "Contents of /vagrant/ssh:"
ls /vagrant/ssh
echo "Contents of /home/$CURRENTUSER/.ssh:"
ls /home/$CURRENTUSER/.ssh
echo "Contents of /home/$CURRENTUSER:"
ls /home/$CURRENTUSER
echo "Done with public key"

echo "Changing permssions of /vagrant/ssh"
chown $CURRENTUSER /vagrant/ssh
chown $CURRENTUSER /vagrant/ssh/*
echo "Done"
