#!/bin/bash -ex

usage() {
    echo "Usage: $0 [-v <version to rollback to>]"
}

while getopts "v:" o; do
    case "${o}" in
        v)
            VERSION=$OPTARG
            ;;
        *)
            usage
            ;;
    esac
done

VERSION=${VERSION:-1.9.11-1}

# remove the neutron plugin WITHOUT removing the plugin
sudo service midonet-cluster stop
sudo cp midonet.list /etc/apt/sources.list.d/midonet.list
sudo apt-get update
sudo apt-get install midolman python-midonetclient=$VERSION
sudo dpkg -r --force-all midonet-cluster midolman midonet-tools

# Assume that if a rollback is being done then a migration has
# been done before this, and therefore the file will exist.
cd run_dm

sudo apt-get install midolman python-midonetclient=$VERSION

sudo service tomcat7 restart

if [ -f PR2ER ]; then
    ./migrate.py -c mig.conf deler
fi

sudo cp neutron.conf /etc/neutron/neutron.conf
sudo service neutron-server restart
