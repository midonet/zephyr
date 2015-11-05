#!/usr/bin/env bash

set -x

SCRIPT_ROOT=$( cd `dirname ${BASH_SOURCE[0]}` ; pwd)
ZEPHYR_ROOT=`dirname $SCRIPT_ROOT`

cd $ZEPHYR_ROOT

# Install the XMLRunner module, as we'll need it to spit
# out JUnit-style XML results files for Jenkins
sudo pip -q install xmlrunner

export ZEPHYR_TEST_JUNIT_OUTDIR=$ZEPHYR_ROOT/test-results

# Run all tests in each package's tests directory
TESTS_TO_RUN=tests.t3.neutron.reliability.test_basic_ping.TestBasicPing
TESTS_TO_RUN="$TESTS_TO_RUN,tests.t3.neutron.features.test_extra_routes.TestExtraRoutes"
TESTS_TO_RUN="$TESTS_TO_RUN,tests.t3.neutron.features.test_port_security.TestPortSecurity"

./tsm-run.py -d -l $ZEPHYR_ROOT/test-logs -r $ZEPHYR_TEST_JUNIT_OUTDIR -c neutron -t $TESTS_TO_RUN
