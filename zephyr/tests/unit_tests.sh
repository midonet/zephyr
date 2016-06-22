#!/usr/bin/env bash

set -x

SCRIPT_ROOT=$( cd `dirname ${BASH_SOURCE[0]}` ; pwd)
ZEPHYR_ROOT=`dirname ${SCRIPT_ROOT}`
ZEPHYR_SOURCE_ROOT=`dirname ${ZEPHYR_ROOT}`
ZEPHYR_PTM_ROOT="${ZEPHYR_SOURCE_ROOT}/zephyr_ptm"

# Install the XMLRunner module, as we'll need it to spit
# out JUnit-style XML results files for Jenkins
sudo pip -q install xmlrunner

export ZEPHYR_TEST_JUNIT_OUTDIR=${ZEPHYR_ROOT}/test-results

# Run all tests in each package's tests directory
ZEPHYR_TEST_PACKAGES="common tsm vtm underlay"

PYTHONPATH=${ZEPHYR_SOURCE_ROOT} ${ZEPHYR_PTM_ROOT}/ptm-ctl.py --startup -d

for dir in ${ZEPHYR_TEST_PACKAGES}; do
  for test in `find ${ZEPHYR_ROOT}/tests/${dir} -name *_test.py`; do
    PYTHONPATH=${ZEPHYR_SOURCE_ROOT} python ${test}
    sleep 3
  done
done

${ZEPHYR_SOURCE_ROOT}/tsm-run.py -d \
    -l ${ZEPHYR_ROOT}/test-logs \
    -r ${ZEPHYR_TEST_JUNIT_OUTDIR} \
    -c neutron \
    -t tests.neutron.reliability.test_basic_ping
RES=$?

PYTHONPATH=${ZEPHYR_SOURCE_ROOT} ${ZEPHYR_PTM_ROOT}/ptm-ctl.py --shutdown -d

exit ${RES}
