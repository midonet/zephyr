#!/usr/bin/env bash

set -x

OS=`python -mplatform | sed -e 's/^.*-with-//' | cut -d '-' -f 1`

if [ ".$OS" == ".Ubuntu" ]; then
  INSTALL='sudo apt-get install -y'

  MIDOKURA_MISC_REPO="deb [arch=amd64] http://repo.midonet.org/misc stable main"
  sudo bash -c "echo $MIDOKURA_MISC_REPO > /etc/apt/sources.list.d/midokura-misc.sources.list"
  curl -L http://repo.midonet.org/RPM-GPG-KEY-midokura | sudo apt-key add -

  ZOOKEEPER="zookeeper zookeeperd"
  TOMCAT="tomcat7"

  sudo apt-add-repository -y ppa:openjdk-r/ppa
  sudo apt-get update

elif [ ".$OS" == ".centos" ]; then
  INSTALL='sudo yum install -y'

  MK_MISC_REPO="[midonet-misc]\nname=MN 3rd Party\nbaseurl=http://repo.midonet.org/misc/RHEL/7/misc/"
  MK_MISC_REPO="$MK_MISC_REPO\nenabled=1\ngpgcheck=1\ngpgkey=http://repo.midonet.org/RPM-GPG-KEY-midokura"
  sudo bash -c "echo $MK_MISC_REPO > /etc/yum.repos.d/midokura-misc.repo"

  ZOOKEEPER="zookeeper zookeeper-server"
  TOMCAT="tomcat"

else
  echo "Must run on CentOS or Ubuntu!"
  exit 1
fi

# Install GIT as a base pre-requisite
$INSTALL git

# Install ZK
$INSTALL $ZOOKEEPER

# Install Quagga
$INSTALL haproxy quagga

# Install HTTPD
$INSTALL $TOMCAT

# Install system tools
$INSTALL wget g++ bridge-utils iptables tcpdump python-pip mz dnsmasq-base

# Use IPv4 forwarding
sudo bash -c "echo 1 > /proc/sys/net/ipv4/ip_forward"

$INSTALL openjdk-7-jre-headless openjdk-7-jdk
$INSTALL openjdk-8-jre-headless openjdk-8-jdk

$INSTALL libcurl4-gnutls-dev

sudo pip install -r requirements.txt

sudo update-alternatives --set java /usr/lib/jvm/java-8-openjdk-amd64/jre/bin/java


