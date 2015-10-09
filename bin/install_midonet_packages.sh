#!/usr/bin/env bash

SCRIPT_ROOT=$( cd `dirname ${BASH_SOURCE[0]}` ; pwd)
ZEPHYR_ROOT=`dirname $SCRIPT_ROOT`

PRODUCT=midonet
VERSION=nightly
ART_DIST=unstable
PLUGIN_DIST=stable
OST_VERSION=kilo
OST_DIST=stable
ART_USER=
ART_PASS=

function usage() {
    set +x
    if [ ".$1" != "." ]; then
        echo "Error: $1"
    fi
    echo "Usage: install_midonet_packages.sh -c <component> -v <version> -d <distribution> -n <plugin_dist>"
    echo "                                   -o <openstack_version> -D <openstack_distribution>"
    echo "                                   [-u <user> -p <pass>]"
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

while [ ".$1" != "." ]; do
    case $1 in
        -c)
            shift
            if ! check_and_set PRODUCT $*; then
                usage "Invalid product: $1"
                exit 1
            fi
            ;;
        -v)
            shift
            if ! check_and_set VERSION $*; then
                usage "Invalid version: $1"
                exit 1
            fi
            ;;
        -d)
            shift
            if ! check_and_set ART_DIST $*; then
                usage "Invalid distribution for midonet: $1"
                exit 1
            fi
            ;;
        -n)
            shift
            if ! check_and_set PLUGIN_DIST $*; then
                usage "Invalid distribution for plugin: $1"
                exit 1
            fi
            ;;
        -o)
            shift
            if ! check_and_set OST_VERSION $*; then
                usage "Invalid OSt version: $1"
                exit 1
            fi
            ;;
        -D)
            shift
            if ! check_and_set OST_DIST $*; then
                usage "Invalid OSt distribution: $1"
                exit 1
            fi
            ;;
        -u)
            shift
            if ! check_and_set ART_USER $*; then
                usage "Invalid username: $1"
                exit 1
            fi
            ;;
        -p)
            shift
            if ! check_and_set ART_PASS $*; then
                usage "Invalid password: $1"
                exit 1
            fi
            ;;
        -h)
            usage ""
            exit 0
            ;;
        *)
            usage "Invalid option: $1"
            exit 1
            ;;
    esac
    shift
done

cd $ZEPHYR_ROOT

./cbt-ctl.py -i midonet-utils

if [ ".$PRODUCT" == ".midonet-mem" ]; then
  ./cbt-ctl.py -i midonet-mem -V $VERSION -D $ART_DIST -U $ART_USER -P $ART_PASS
elif [ ".$PRODUCT" == ".midonet" ]; then
  ./cbt-ctl.py -i midonet -V $VERSION -D $ART_DIST
else
  echo "Product must be either 'midonet' or 'midonet-mem'"
  exit 1
fi

./cbt-ctl.py -i plugin -V $OST_VERSION -D $PLUGIN_DIST


