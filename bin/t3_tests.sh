#!/usr/bin/env bash
set -x
export DEBIAN_FRONTEND=noninteractive

mn_version=$1
ost_version=$2
TESTS=$3

# Set up parameters and settings
ZEPHYR_ROOT=`pwd`
ART_SERVER="http://artifactory.bcn.midokura.com/artifactory"

NEUTRON_OPTS="--os-url=http://localhost:9696 \
            --os-token=admin \
            --os-auth-url=http://hostname:5000/v2.0 \
            --os-auth-strategy=noauth"

if [ x"${TESTS}" = "x" ]; then
TESTS1="\
  tests.neutron.reliability,tests.neutron.api,\
  tests.neutron.features.network.security_groups,\
  tests.neutron.features.network.test_allowed_address_pairs,\
  tests.neutron.features.network.test_external_connectivity,\
  tests.neutron.features.network.test_extra_routes,\
  tests.neutron.features.network.test_floating_ip,\
  tests.neutron.features.network.test_multi_subnet,\
  tests.neutron.features.security,tests.neutron.features.fwaas"
else
TESTS1=${TESTS}
fi

TESTS2="\
tests.neutron.features.network.bgp_ip"
TESTS3="\
tests.neutron.features.network.bgp_ip,\
tests.neutron.features.network.router_peering"

# Set variables based on OST_VERSION and MN_VERSION
midonet_api_url='http:\/\/localhost:8181\/midonet-api'
midonet_db_manage='neutron-db-manage --subproject networking-midonet'
if [ "x${mn_version}" = "x1.9" ]; then
    mn_repo='mem-1.9'
    mn_dist='unstable'
    use_cluster='false'
    neutron_core_pkg='neutron.plugins.midonet.plugin.MidonetPluginV2'
    midonet_core_api_pkg='midonet-api'
    midonet_api_url='http:\/\/localhost:8080\/midonet_api'
    java_ver='7'
else
    mn_repo='midonet-5.2'
    mn_dist='unstable'
    neutron_core_pkg='midonet.neutron.plugin_v2.MidonetPluginV2'
    midonet_core_api_pkg='midonet-cluster midonet-tools'
    java_ver='8'
fi

if [ "x${ost_version}" = "xkilo" ]; then
      plugin_dist='stable'
      service_plugins='lbaas'
      plugin_package='python-neutron-plugin-midonet'
      l2gw_service_provider=''
      lbaas_service_provider=''
      midonet_db_manage='midonet-db-manage'
elif [ "x${ost_version}" = "xliberty" ]; then
      plugin_dist='stable'
      service_plugins="midonet.neutron.services.l3.l3_midonet.MidonetL3ServicePlugin,neutron_lbaas.services.loadbalancer.plugin.LoadBalancerPlugin"
      l2gw_service_provider="L2GW:midonet:midonet.neutron.services.l2gateway.service_drivers.l2gw_midonet.MidonetL2gwDriver:default"
      lbaas_service_provider="LOADBALANCER:Midonet:midonet.neutron.services.loadbalancer.driver.MidonetLoadbalancerDriver:default"
      plugin_package='python-networking-midonet'
else
      plugin_dist='unstable'
      service_plugins="midonet.neutron.services.l3.l3_midonet.MidonetL3ServicePlugin,neutron_lbaas.services.loadbalancer.plugin.LoadBalancerPlugin,midonet.neutron.services.gw_device.plugin.MidonetGwDeviceServicePlugin,midonet.neutron.services.firewall.plugin.MidonetFirewallPlugin,midonet.neutron.services.l2gateway.plugin.MidonetL2GatewayPlugin,midonet.neutron.services.bgp.plugin.MidonetBgpPlugin,midonet.neutron.services.logging_resource.plugin.MidonetLoggingResourcePlugin"
      l2gw_service_provider="L2GW:midonet:midonet.neutron.services.l2gateway.service_drivers.l2gw_midonet.MidonetL2gwDriver:default"
      lbaas_service_provider="LOADBALANCER:Midonet:midonet.neutron.services.loadbalancer.driver.MidonetLoadbalancerDriver:default"
      plugin_package='python-networking-midonet'
fi
plugin_repo="openstack-${ost_version}-deb"

sudo bash -c "echo 1 > /proc/sys/net/ipv4/ip_forward"

# Set up packages
if [ "{java-ver}" = "7" ]; then
sudo apt-get install openjdk-7-jdk
sudo update-alternatives --set java /usr/lib/jvm/java-7-openjdk-amd64/jre/bin/java
else
sudo apt-add-repository ppa:openjdk-r/ppa
sudo apt-get update -qq
sudo apt-get install openjdk-8-jdk
fi

sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 5EDB1B62EC4926EA
sudo add-apt-repository -y "deb ${ART_SERVER}/${mn_repo}-deb ${mn_dist} main"
sudo add-apt-repository -y "deb ${ART_SERVER}/misc-deb stable main"
sudo add-apt-repository -y "deb ${ART_SERVER}/${plugin_repo} ${plugin_dist} main"
sudo add-apt-repository -y "cloud-archive:${ost_version}"

curl "${ART_SERVER}/api/gpg/key/public" | sudo apt-key add -

sudo apt-get update -qq

sudo pip install -r requirements.txt

sudo apt-get install -y --allow-unauthenticated \
  zookeeper zookeeperd \
  tomcat7 haproxy quagga \
  wget g++ bridge-utils iptables tcpdump python-pip mz dnsmasq-base \
  libcurl4-gnutls-dev \
  midolman \
  python-midonetclient \
  python-midonetclient \
  python3-software-properties \
  zkdump \
  nmap \
  python-neutron-vpnaas \
  python-neutron-fwaas \
  python-neutron-lbaas \
  python-oslo-log \
  ${plugin_package} \
  ${midonet_core_api_pkg}

./install_neutron.py -v "${ost_version}"

sudo pip install --upgrade pbr
if [ "${ost_version}" = "kilo" ]; then
sudo pip install networking-l2gw==2015.1.1
else
sudo sed '$ a[service_providers]' -i /etc/neutron/neutron.conf
sudo sed "$ aservice_provider=${l2gw_service_provider}" -i /etc/neutron/neutron.conf
sudo sed "$ aservice_provider=${lbaas_service_provider}" -i /etc/neutron/neutron.conf

sudo pip install networking-l2gw
fi

# Set up neutron configuration files with relevant settings
sudo sed -i \
-e "s/service_plugins =.*/service_plugins = ${service_plugins}/" \
/etc/neutron/neutron.conf

echo "Replaced service plugins in neutron.conf:"
sudo grep "service_plugins =" /etc/neutron/neutron.conf

sudo sed -i -e "s/core_plugin =.*/core_plugin = ${neutron_core_pkg}/" /etc/neutron/neutron.conf
sudo sed -i -e "s/midonet_uri =.*/midonet_uri = ${midonet_api_url}/" /etc/neutron/plugin.ini

echo "Current neutron.conf:"
sudo cat /etc/neutron/neutron.conf

echo "Current l2gw_plugin.ini:"
sudo cat /etc/neutron/l2gw_plugin.ini

echo "Current plugin.ini:"
sudo cat /etc/neutron/plugin.ini

echo "Current midoent package dir:"
find /usr/lib/python2.7/dist-packages/midonet -name "*.py" | grep -v __init

echo "Midolman package versions"
dpkg -l "mido*"

# watchdog apparently doesn't work correctly when dealing with net namespaces
sudo mv /usr/bin/wdog /usr/bin/wdog-dontuse

sudo service neutron-server restart
sudo service neutron-server status

# Wait for neutron to start
tries=0
while ! neutron ${NEUTRON_OPTS} ext-list --tenant-id=admin > /dev/null; do
sleep 1
tries=$((tries+1))
if [ "$tries" -gt "60" ]; then
  echo "Couldn't access neutron server, quitting"
  echo "<testsuite errors='0' failures='1' name='Dummy' tests='1'>\
  <testcase name='DummyCase'><failure>Neutron Never Started</failure></testcase>\
  </testsuite>" > dummy-result.xml

  sudo mkdir test-logs
  sudo cp /var/log/neutron/neutron-server.log test-logs
  sudo tar cvfz test-logs/neutron-conf.tgz /etc/neutron/*

  tar cvf test-logs.tar test-logs && gzip -9 test-logs.tar

  exit 1
fi
done

set +e

sudo modprobe openvswitch

echo "Neutron Loaded Extensions:"
neutron ${NEUTRON_OPTS} ext-list --tenant-id=admin
neutron ${NEUTRON_OPTS} quota-update \
--router -1 --subnet -1 --network -1 --port -1 \
--tenant-id=admin

# Run Zephyr Tests
export PYTHONPATH=.

###############################################
# TEST1 - 1 zookeeper, 2 computes, 1 edge
###############################################
TESTS_TO_RUN=`echo ${TESTS1} | sed "s/, */,/g"`
zephyr_ptm/ptm-ctl.py --startup -d -c 1z-2c-1edge.json
echo "cluster.loggers.root : DEBUG" | mn-conf set
./tsm-run.py -d \
-l ${ZEPHYR_ROOT}/test-logs \
-r ${ZEPHYR_ROOT}/test-results \
-t ${TESTS_TO_RUN}
zephyr_ptm/ptm-ctl.py --shutdown -d -c 1z-2c-1edge.json
sudo neutron-db-manage upgrade head
sudo ${midonet_db_manage} upgrade head

mkdir ${ZEPHYR_ROOT}/test-logs/run_1
sudo tar cvfz ${ZEPHYR_ROOT}/test-logs/run_1/midolman-logs.tgz /var/log/midolman.*
sudo tar cvfz ${ZEPHYR_ROOT}/test-logs/run_1/midonet-cluster-logs.tgz /var/log/midonet-cluster
sudo cp /var/log/neutron/neutron-server.log ${ZEPHYR_ROOT}/test-logs/run_1/neutron-server.log
mv ${ZEPHYR_ROOT}/test-logs/zephyr-output.log ${ZEPHYR_ROOT}/test-logs/run_1

# Only run next tests if specific tests weren't specified for this job
if [ ".${TESTS}" = "." ]; then
###############################################
# TEST2 - 2 zookeepers, 1 compute+edge
###############################################
TESTS_TO_RUN=`echo ${TESTS2} | sed "s/, */,/g"`

# Run BGP tests on special topo
zephyr_ptm/ptm-ctl.py --startup -d -c 2z-1c.json
./tsm-run.py -d \
  -l ${ZEPHYR_ROOT}/test-logs \
  -r ${ZEPHYR_ROOT}/test-results \
  -t ${TESTS_TO_RUN}
zephyr_ptm/ptm-ctl.py --shutdown -d -c 2z-1c.json
sudo neutron-db-manage upgrade head
sudo ${midonet_db_manage} upgrade head

mkdir ${ZEPHYR_ROOT}/test-logs/run_2
sudo tar cvfz ${ZEPHYR_ROOT}/test-logs/run_2/midolman-logs.tgz /var/log/midolman.*
sudo tar cvfz ${ZEPHYR_ROOT}/test-logs/run_2/midonet-cluster-logs.tgz /var/log/midonet-cluster
sudo cp /var/log/neutron/neutron-server.log ${ZEPHYR_ROOT}/test-logs/run_2/neutron-server.log
mv ${ZEPHYR_ROOT}/test-logs/zephyr-output.log ${ZEPHYR_ROOT}/test-logs/run_2

###############################################
# TEST3 - 2 zookeepers, 1 compute (not in NetNS), 2 tunnel-edges
###############################################
TESTS_TO_RUN=`echo ${TESTS3} | sed "s/, */,/g"`

# Run BGP+RP tests on special topo
zephyr_ptm/ptm-ctl.py --startup -d -c 2z-1c-root-2tun.json
./tsm-run.py -d \
  -l ${ZEPHYR_ROOT}/test-logs \
  -r ${ZEPHYR_ROOT}/test-results \
  -t ${TESTS_TO_RUN}
zephyr_ptm/ptm-ctl.py --shutdown -d -c 2z-1c-root-2tun.json

mkdir ${ZEPHYR_ROOT}/test-logs/run_3
sudo cp /var/log/neutron/neutron-server.log ${ZEPHYR_ROOT}/test-logs/run_3/neutron-server.log
sudo tar cvfz ${ZEPHYR_ROOT}/test-logs/run_3/midolman-logs.tgz /var/log/midolman.*
sudo tar cvfz ${ZEPHYR_ROOT}/test-logs/run_3/midonet-cluster-logs.tgz /var/log/midonet-cluster
mv ${ZEPHYR_ROOT}/test-logs/zephyr-output.log ${ZEPHYR_ROOT}/test-logs/run_3
fi

find test-results -name *.xml

sudo tar cvfz ${ZEPHYR_ROOT}/test-logs/neutron-conf.tgz /etc/neutron/*

tar cvf zephyr-logs.tar /tmp/zephyr/logs && gzip -9 zephyr-logs.tar
tar cvf test-logs.tar test-logs && gzip -9 test-logs.tar
tar cvf test-results.tar test-results && gzip -9 test-results.tar
