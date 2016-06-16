#!/usr/bin/env bash

set -x

SCRIPT_ROOT=$( cd `dirname ${BASH_SOURCE[0]}` ; pwd)
ZEPHYR_PTM_ROOT=`dirname ${SCRIPT_ROOT}`
ZEPHYR_SOURCE_ROOT=`dirname ${ZEPHYR_PTM_ROOT}`

# Install the XMLRunner module, as we'll need it to spit
# out JUnit-style XML results files for Jenkins
sudo pip -q install xmlrunner

export ZEPHYR_TEST_JUNIT_OUTDIR=${ZEPHYR_PTM_ROOT}/test-results

# Run all tests in each package's tests directory
ZEPHYR_PTM_TEST_PACKAGES="ptm"

for dir in ${ZEPHYR_PTM_TEST_PACKAGES}; do
  for test in `find ${ZEPHYR_PTM_ROOT}/tests/${dir} -name *_test.py`; do
    PYTHONPATH=${ZEPHYR_SOURCE_ROOT} python ${test}
    sleep 3
  done
done
