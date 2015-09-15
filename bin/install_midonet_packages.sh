#!/usr/bin/env bash

VERSION=
PKG_AUTH_METHOD="http"
PKG_AUTH_USER=
PKG_AUTH_PASS=
PKG_SERVER=
PKG_DIST=
PKG_COMPONENT="main"

# APT-GET repository if we use the artifactory server
ART_SERVER="artifactory-dev.bcn.midokura.com/artifactory/midonet"

# CURL URI to use to fetch the GPG key for artifactory
ART_CURL_URI="http://artifactory-dev.bcn.midokura.com/artifactory/api/gpg/key/public"

# Distribution to use for artifactory package
ART_DIST="stable"

UBUNTU=
CENTOS=

OS=`python -mplatform | sed -e 's/^.*-with-//' | cut -d '-' -f 1`

if [ ".$OS" == ".Ubuntu" ]; then
  UBUNTU=true
  INSTALL="sudo apt-get install -y"
  REPO_FILE="/etc/apt/sources.list.d/midonet-artifactory.list"
elif [ ".$OS" == ".centos" ]; then
  CENTOS=true
  INSTALL="sudo yum install -y"
  REPO_FILE="/etc/yum.repos.d/midonet-artifactory.repo"
else
  echo "Must run on CentOS or Ubuntu!"
  exit 1
fi


function usage() {
  echo "Usage: install_midonet_packages.sh -v <version>"
  if [ ".$1" != "." ]; then
    echo "Error: $1"
  fi
}

function check_and_set() {
    # param1 = var to set
    # param2 = argument line
    #
    # Check that the next argument line string doesn't indicate a new argument (starts
    # with '-') and is present.  If both are true, set the var indicated in param1 to
    # the value and return 0, otherwise don't set and return 1
    VAR=$1
    shift
    if [ $# -eq 0 ]; then
        return 1
    fi

    if printf '%s' $1 | grep -q "^-"; then
        return 1
    fi

    eval $VAR=$1
    return 0
}

function install_package_from_repo() {
    # Pull down MN from a repository (standard apt-get repo or artifactory apt-get repo)
    SERVER_LINE="$PKG_AUTH_METHOD://"
    if [ ".$PKG_USE_AUTH" == ".true" ]; then
        SERVER_LINE=$SERVER_LINE"$PKG_AUTH_USER:$PKG_AUTH_PASS@"
    fi
    SERVER_LINE="$SERVER_LINE$PKG_SERVER"

    echo "Installing midonet from packages at $SERVER_LINE $PKG_DIST PKG_COMPONENT"

    set -e

    # add midokura apt to sources list
    sudo bash -c "echo deb [arch=all] $SERVER_LINE $PKG_DIST PKG_COMPONENT > $REPO_FILE"
    if [ ".$UBUNTU" == ".true" ]; then
      curl -k $CURL_URI | sudo apt-key add - && true
      sudo apt-get update
    fi

    # Install midolman packages
    $ECHO sudo apt-get install -y midolman
    $ECHO sudo update-rc.d midolman enable

    $ECHO sudo apt-get install -y python-midonetclient
    $ECHO sudo apt-get -o Dpkg::Options::="--force-confnew" install -y midonet-api
    set +e
}

VERSION=''

# Check all script arguments
while [ ".$1" != "." ]; do
  case $1 in
    -v | --version ) # Install this version
      shift
      if ! check_and_set VERSION $*; then
        usage "Invalid directory for mdts_root: $1"
        exit 1
      fi
      shift
      ;;
    *)
      ;;
  esac
done




