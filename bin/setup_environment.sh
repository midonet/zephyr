#!/usr/bin/env bash

set -x

OS=`python -mplatform | sed -e 's/^.*-with-//' | cut -d '-' -f 1`

if [ ".$OS" == ".Ubuntu" ]; then
  INSTALL='sudo apt-get install -y'

  CASSANDRA_REPO="deb http://debian.datastax.com/community stable main"
  sudo bash -c "echo $CASSANDRA_REPO > /etc/apt/sources.list.d/cassandra.sources.list"
  curl -L http://debian.datastax.com/debian/repo_key | sudo apt-key add -
  CASSANDRA="dsc20=2.0.16-1 cassandra=2.0.16"

  MIDOKURA_MISC_REPO="deb [arch=amd64] http://repo.midonet.org/misc stable main"
  sudo bash -c "echo $MIDOKURA_MISC_REPO > /etc/apt/sources.list.d/midokura-misc.sources.list"
  curl -L http://repo.midonet.org/RPM-GPG-KEY-midokura | sudo apt-key add -

  ZOOKEEPER="zookeeper zookeeperd"
  TOMCAT="tomcat7"

  sudo apt-get update
elif [ ".$OS" == ".centos" ]; then
  INSTALL='sudo yum install -y'

  CASS_REPO="[datastax]\nname = Cassandra Repo\nbaseurl = http://rpm.datastax.com/community\nenabled = 1\ngpgcheck = 0"
  sudo bash -c "echo $CASS_REPO > /etc/yum.repos.d/cassandra.repo"
  CASSANDRA="dsc20-2.0.16-1 cassandra-2.0.16"

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

# Install Cassandra and ZK
$INSTALL $CASSANDRA $ZOOKEEPER

# Install Quagga
$INSTALL haproxy quagga

# Install HTTPD
$INSTALL $TOMCAT

# Install system tools
$INSTALL wget g++ bridge-utils iptables tcpdump python-pip mz dnsmasq-base

# Install Python tools
sudo pip install unittest2 numpy setuptools pyyaml futures pyhamcrest

# Use IPv4 forwarding
sudo bash -c "echo 1 > /proc/sys/net/ipv4/ip_forward"

