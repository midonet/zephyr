#!/usr/bin/env bash

set -x

SCRIPT_ROOT=$( cd `dirname ${BASH_SOURCE[0]}` ; pwd)
ZEPHYR_ROOT=`dirname $SCRIPT_ROOT`

# Install the XMLRunner module, as we'll need it to spit
# out JUnit-style XML results files for Jenkins
sudo pip -q install xmlrunner

export ZEPHYR_TEST_JUNIT_OUTDIR=$ZEPHYR_ROOT/test-results

# Run all tests in each package's tests directory
TEST_PACKAGES="common PTM VTM TSM"

for dir in $TEST_PACKAGES; do
  for test in `find $dir/tests -name *Test.py`; do
    PYTHONPATH=. python $test
    sleep 3
  done
done

set -e

$ZEPHYR_ROOT/tsm-run.py -d -l $ZEPHYR_ROOT/test-logs -r $ZEPHYR_TEST_JUNIT_OUTDIR \
    -c midonet \
    -t tests.mn_api.reliability.test_basic_ping

$ZEPHYR_ROOT/tsm-run.py -d -l $ZEPHYR_ROOT/test-logs -r $ZEPHYR_TEST_JUNIT_OUTDIR \
    -c neutron \
    -t tests.neutron.reliability.test_basic_ping

